"""
Simple, comprehensive test suite for vastpy CLI parameter handling.
"""
import sys
import os
import tempfile
import json
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to import vastpy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vastpy.cli import main, process_parameters
from vastpy import VASTClient


class MockPoolManager:
    """Simple mock pool manager to capture HTTP requests."""
    
    def __init__(self):
        self.last_request = None
        
    def request(self, method, url, headers=None, fields=None, body=None):
        self.last_request = {
            'method': method,
            'fields': fields,
            'body': body,
            'headers': headers
        }
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'{"success": true}'
        mock_response.headers = {"Content-Type": "application/json"}
        return mock_response


class TestParameterHandling(unittest.TestCase):
    """Comprehensive tests for parameter handling with minimal complexity."""
    
    def setUp(self):
        self.mock_pool_manager = MockPoolManager()

    def test_parameter_classification(self):
        """Test that parameters are correctly classified for different HTTP methods."""
        # GET: all params become query params
        query, data = process_parameters('get', [('page', '1')], [('active', 'true')], [('name', 'John')], None)
        self.assertEqual(query, {'page': 1 , 'name': 'John'})
        self.assertEqual(data, {'active': True})
        
        # POST: split between query and data
        query, data = process_parameters('post', [('notify', 'true')], [('role', 'admin')], [('name', 'John')], None)
        self.assertEqual(query, {'notify': True})
        self.assertEqual(data, {'name': 'John', 'role': 'admin'})
        
        # DELETE: all params become query params
        query, data = process_parameters('delete', [('force', 'true')], [('cascade', 'true')], [('reason', 'test')], None)
        self.assertEqual(query, {'force': True, 'reason': 'test'})
        self.assertEqual(data, {'cascade': True})
        
        # Test duplicate key merging: x=3, --dparam x=7 → x=[3,7]
        query, data = process_parameters('post', [], [('x', '7')], [('x', '3'), ('y', '5')], None)
        self.assertEqual(data, {'x': [7, 3], 'y': 5})

    @patch('vastpy.urllib3.PoolManager')
    @patch('vastpy.urllib3.disable_warnings')
    def test_cli_integration(self, mock_disable_warnings, mock_pool_manager_class):
        """Test complete CLI flow from arguments to HTTP request."""
        mock_pool_manager_class.return_value = self.mock_pool_manager
        
        # Test explicit-only parameters (cleanest approach)
        test_args = [
            'vastpy-cli', '--address', 'test.com', '--user', 'test', '--password', 'test',
            '--qparam', 'page=1', '--qparam', 'limit=10',
            'get', 'users'
        ]
        
        with patch.object(sys, 'argv', test_args):
            main()
        
        request = self.mock_pool_manager.last_request
        self.assertEqual(request['method'], 'GET')
        self.assertEqual(sorted(request['fields']), sorted([('page', 1), ('limit', 10)]))
        self.assertIsNone(request['body'])
        
        # Test POST with mixed params and file input
        test_data = {"a": {"b": "c", "d": ["x", "y"]}, "f" : [1,2,3], "r" : True}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name
        
        try:
            test_args = [
                'vastpy-cli', '--address', 'test.com', '--user', 'test', '--password', 'test',
                '--qparam', 'notify=true', '--file-input', temp_file,
                'post', 'users'
            ]
            
            with patch.object(sys, 'argv', test_args):
                main()
            
            request = self.mock_pool_manager.last_request
            self.assertEqual(request['method'], 'POST')
            self.assertEqual(request['fields'], [('notify', True)])
            body_data = json.loads(request['body'].decode('utf-8'))
            self.assertEqual(body_data, test_data)
        finally:
            os.unlink(temp_file)

    @patch('vastpy.urllib3.PoolManager')  
    @patch('vastpy.urllib3.disable_warnings')
    def test_backward_compatibility(self, mock_disable_warnings, mock_pool_manager_class):
        """Test that legacy usage patterns still work."""
        mock_pool_manager_class.return_value = self.mock_pool_manager
        
        # Legacy POST usage
        test_args = [
            'vastpy-cli', '--address', 'test.com', '--user', 'test', '--password', 'test',
            'post', 'users', 'name=John', 'email=john@example.com'
        ]
        
        with patch.object(sys, 'argv', test_args):
            main()
        
        request = self.mock_pool_manager.last_request
        self.assertEqual(request['method'], 'POST')
        self.assertEqual(request['fields'], None)  # No query params
        body_data = json.loads(request['body'].decode('utf-8'))
        self.assertEqual(body_data, {'name': 'John', 'email': 'john@example.com'})

    @patch('vastpy.urllib3.PoolManager')
    @patch('vastpy.urllib3.disable_warnings')
    def test_authentication_headers(self, mock_disable_warnings, mock_pool_manager_class):
        """Test that tenant name and token headers are correctly sent."""
        mock_pool_manager_class.return_value = self.mock_pool_manager
        
        # Test with tenant name and basic auth
        test_args = [
            'vastpy-cli', '--address', 'test.com', '--user', 'test', '--password', 'test',
            '--tenant-name', 'my-tenant', 'get', 'users'
        ]
        
        with patch.object(sys, 'argv', test_args):
            main()
        
        request = self.mock_pool_manager.last_request
        headers = request.get('headers', {})
        self.assertIn('X-Tenant-Name', headers)
        self.assertEqual(headers['X-Tenant-Name'], 'my-tenant')
        self.assertIn('authorization', headers)  # Basic auth header
        
        # Test with token authentication
        test_args = [
            'vastpy-cli', '--address', 'test.com', '--token', 'my-secret-token',
            '--tenant-name', 'token-tenant', 'get', 'status'
        ]
        
        with patch.object(sys, 'argv', test_args):
            main()
        
        request = self.mock_pool_manager.last_request
        headers = request.get('headers', {})
        self.assertIn('authorization', headers)
        self.assertEqual(headers['authorization'], "'Api-Token my-secret-token")
        self.assertIn('X-Tenant-Name', headers)
        self.assertEqual(headers['X-Tenant-Name'], 'token-tenant')
        
        # Test without tenant name (header should not be present)
        test_args = [
            'vastpy-cli', '--address', 'test.com', '--token', 'my-token',
            'get', 'status'
        ]
        
        with patch.object(sys, 'argv', test_args):
            main()
        
        request = self.mock_pool_manager.last_request
        headers = request.get('headers', {})
        self.assertIn('authorization', headers)
        self.assertNotIn('X-Tenant-Name', headers)  # Should not be present


if __name__ == '__main__':
    unittest.main()