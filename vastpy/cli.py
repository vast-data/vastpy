import os
import sys
import json
import argparse

from . import VASTClient, RESTFailure

OPERATIONS = ['get', 'post', 'patch', 'delete']

def key_value_pair(s):
    key, value = s.split('=', 1)
    return (key, value)

def pairs_to_multidict(l):
    result = {}
    for key, value in l:
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            if value.isdigit():
                value = int(value)
            # default: string

        if key in result:
            if isinstance(result[key], list):
                result[key].append(value)
            else:
                result[key] = [result[key], value]
        else:
            result[key] = value
    return result

def merge_param_dicts(base_dict, new_dict):
    """
    Merge two parameter dictionaries, creating lists for duplicate keys.
    Similar to pairs_to_multidict logic but for merging existing dicts.
    """
    result = dict(base_dict)  # Start with a copy of base_dict
    
    for key, value in new_dict.items():
        if key in result:
            # Key exists in base dict, need to merge values
            existing_value = result[key]
            if isinstance(existing_value, list):
                # Existing value is already a list, append new value
                if isinstance(value, list):
                    result[key].extend(value)
                else:
                    result[key].append(value)
            else:
                # Existing value is single, create list with both values
                if isinstance(value, list):
                    result[key] = [existing_value] + value
                else:
                    result[key] = [existing_value, value]
        else:
            # Key doesn't exist, just add it
            result[key] = value
    
    return result

def process_parameters(operation, qparam, dparam, params, file_input):
    """
    Process CLI parameters and determine final query and data parameters based on HTTP method.
    
    Args:
        operation: HTTP method (get, post, patch, etc.)
        qparam: List of --qparam tuples
        dparam: List of --dparam tuples  
        params: List of legacy parameter tuples
        file_input: File path for JSON input or None
    
    Returns:
        tuple: (query_params_dict, data_params_dict)
    """
    # Parse all parameter types
    query_params = pairs_to_multidict(qparam) if qparam else {}
    data_params = pairs_to_multidict(dparam) if dparam else {}
    legacy_params = pairs_to_multidict(params) if params else {}
    
    # Handle file input
    file_data = None
    if file_input:
        try:
            with open(file_input, 'r') as j:
                file_data = json.load(j)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading JSON file: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Determine parameter placement based on HTTP method
    operation_lower = operation.lower()
    
    if operation_lower in ['get', 'delete', 'options']:
        # These methods: all parameters go to query string
        final_query_params = merge_param_dicts(dict(query_params), legacy_params)
        return final_query_params, dict(data_params)
        
    elif operation_lower in ['post', 'patch', 'put']:       
        # Determine body data with precedence: file_data > dparam + legacy
        if file_data is not None:
            final_data_params = file_data
        else:
            final_data_params = merge_param_dicts(dict(data_params), legacy_params)
        
        return dict(query_params), final_data_params
    
    else:
        print(f"The {operation} operation is not supported")
        sys.exit(1)

def multiline_string(value):
    if isinstance(value, dict):
        if not value:
            return ['']
        return [f'{k}: {v}' for k, v in value.items()]
    return [str(value)]

def tabulate(data):
    """
    1. Stringify every element
    2. Calculate it's width and height
    # 3. Calculate the screen size and force overwrapping if needed
    4. Print it!
    """
    key_to_width = {}
    objects = []
    for i in data:
        obj = {}
        for key, value in i.items():
            value = multiline_string(value)
            obj[key] = value
            longest_row = max(len(i) for i in value)
            key_to_width[key] = max(key_to_width.get(key, 0), len(key), longest_row)
        objects.append(obj)

    # print header
    key_to_width_items = list(key_to_width.items())
    for index, (key, width) in enumerate(key_to_width_items):
        print(key.ljust(width + 1), end='')
        if index < len(key_to_width_items) - 1:
            print('|', end='')
    print()

    # print separator
    for _, width in key_to_width.items():
        print('-' * (width + 1) + '+', end='')
    print()

    # print rows
    for obj in objects:
        row_index = 0
        while True:
            key_to_width_items = list(key_to_width.items())
            should_continue = False
            for index, (key, width) in enumerate(key_to_width_items):
                if obj.get(key):
                    value = obj[key].pop()
                    should_continue = should_continue or bool(obj[key])
                else:
                    value = ''
                print(value.ljust(width + 1), end='')
                if index < len(key_to_width_items) - 1:
                    print('|', end='')
            if not should_continue:
                break
            print()
        print()

def prepare_parser():
    parser = argparse.ArgumentParser(description='vastpy/vastpy-cli are the VAST Data Platform RESTful API SDK and lightweight CLI')
    def add_argument(key, *args, **kwargs):
        if key in os.environ:
            kwargs['required'] = False
            kwargs['default'] = os.environ[key]
            parser.add_argument(*args, **kwargs)
        else:
            parser.add_argument(*args, **kwargs)
    
    add_argument('VMS_USER', '--user', help='VMS user name')
    add_argument('VMS_PASSWORD', '--password', help='VMS password')
    add_argument('VMS_ADDRESS', '--address', required=True, help='VMS address or host name')
    add_argument('VMS_TENANT_NAME', '--tenant-name', help='VMS Tenant Name or VMS Tenant Domain')
    add_argument('VMS_TOKEN', '--token', help='VMS API Token')
    add_argument('VMS_CERT_FILE', '--cert-file', help='Path to custom SSL certificate for VMS')
    add_argument('VMS_CERT_SERVER', '--cert-server-name', help='Address of custom SSL certificate authority')
    add_argument('VMS_API_VERSION', '--api-version', help='API version')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('-i', '--file-input', help='JSON file with as body for POST/PATCH operations')
    parser.add_argument('--qparam', action='append', type=key_value_pair, help='Query parameter in the following format: key=value (can be used multiple times)')
    parser.add_argument('--dparam', action='append', type=key_value_pair, help='Data/body parameter in the following format: key=value (can be used multiple times)')
    parser.add_argument('operation', type=str, choices=OPERATIONS)
    parser.add_argument('endpoint', type=str)
    parser.add_argument('params', type=key_value_pair, nargs='*')
    return parser

def main():
    args = prepare_parser().parse_args()
    client = VASTClient(user=args.user,
                        password=args.password,
                        address=args.address,
                        cert_file=args.cert_file,
                        cert_server_name=args.cert_server_name,
                        tenant=args.tenant_name,
                        token=args.token,
                        version=args.api_version)
    method = getattr(client[args.endpoint], args.operation)

    # Process parameters based on HTTP method and CLI arguments
    query_params, data_params = process_parameters(
        args.operation, 
        args.qparam, 
        args.dparam, 
        args.params, 
        args.file_input
    )

    try:
        # Call HTTP method with processed parameters
        result = method(query_params=query_params if query_params else None,
         data_params=data_params if data_params else None)
    except RESTFailure as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    if isinstance(result, bytes):
        print(result.decode('utf-8'))
    elif isinstance(result, (list, dict)) and not args.json:
        if result:
            if isinstance(result, dict):
                if 'results' in result:
                    if 'prop_list' in result: # vast-db endpoints like /vastauditlog/query_data
                        assert isinstance(result['results'], list)
                        result = [dict(zip(result['prop_list'], i)) for i in result['results']]
                    else: # vms-db endpoints like /events
                        result = result['results']
                else: # single document like /events/123
                    result = [dict(property=k, value=v) for k, v in result.items()]
            tabulate(result)
    else: # json document
        print(json.dumps(result, indent=2))
