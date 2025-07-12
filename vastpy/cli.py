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

    params = {}
    if args.file_input:
        try:
            with open(args.file_input, 'r') as j:
                params = json.load(j)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading JSON file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        params = pairs_to_multidict(args.params)
    try:
        result = method(**params)
    except RESTFailure as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    if isinstance(result, bytes):
        print(result.decode('utf-8'))
    elif isinstance(result, (list, dict)) and not args.json:
        if result:
            if isinstance(result, dict):
                result = [dict(property=k, value=v) for k, v in result.items()]
            tabulate(result)
    else: # json document
        print(json.dumps(result, indent=2))
