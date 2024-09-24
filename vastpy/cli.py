import os
import sys
import json
import argparse

from . import VASTClient, RESTFailure

OPERATIONS = ['get', 'post', 'patch', 'delete']

def key_value_pair(s):
    key, value = s.split('=')
    return (key, value)

def prepare_parser():
    parser = argparse.ArgumentParser(description='vastpy/vastcli are the VAST Data Platform RESTful API SDK and ligthweight CLI')
    def add_argument(key, *args, **kwargs):
        if key in os.environ:
            kwargs['required'] = False
            kwargs['default'] = os.environ[key]
            parser.add_argument(*args, **kwargs)
        else:
            parser.add_argument(*args, **kwargs)
    
    add_argument('VMS_USER', '--user', required=True, help='VMS user name')
    add_argument('VMS_PASSWORD', '--password', required=True, help='VMS password')
    add_argument('VMS_ADDRESS', '--address', required=True, help='VMS address or host name')
    add_argument('VMS_CERT_FILE', '--cert-file', help='Path to custom SSL certificate for VMS')
    add_argument('VMS_CERT_SERVER', '--cert-server-name', help='Address of custom SSL certificate authority')

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
                        cert_server_name=args.cert_server_name)
    method = getattr(client[args.endpoint], args.operation)
    try:
        result = method(**dict(args.params))
    except RESTFailure as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(result, bytes):
        result = json.dumps(result, indent=2)
    print(result)