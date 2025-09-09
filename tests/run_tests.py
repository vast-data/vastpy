#!/usr/bin/env python3
"""
Simple test runner for vastpy tests.
"""
import sys
import unittest
import os

# Add the parent directory to sys.path to import vastpy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

if __name__ == '__main__':
    # Run the simple test suite
    from test_simple import TestParameterHandling
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestParameterHandling)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)