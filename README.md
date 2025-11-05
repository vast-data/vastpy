# VASTPY

A Python SDK for interacting with the VAST Management System (VMS) REST API. This package provides a simple and intuitive interface to manage your VAST storage system programmatically.

## Features

- Full REST API coverage with a Pythonic interface
- Command-line interface (CLI) for quick operations
- Support for all HTTP methods (GET, POST, PATCH, DELETE)
- JSON file input support for complex operations
- Schema-less design compatible with all VAST versions

## Installation

```bash
pip install vastpy
```

The package is available on PyPI: https://pypi.org/project/vastpy/

## Requirements

- Python 3.6 or higher
- urllib3 1.2 or higher

## Quick Start

### Python SDK

#### Authentication

```python
from vastpy import VASTClient

# Initialize with credentials
client = VASTClient(
    user='your_username',
    password='your_password',
    address='vast-vms-hostname',
    token='api-token' # Please provide either an API token for authentication or user + password. API tokens are supported for Vast versions 5.3 and later
    tenant_name='tenant-name' # An optional field, supported for Vast versions 5.3 and later
    version='api-version' # An optional field, defaults to oldest API
)
```
### Obtainig an API Token - Vast 5.3+
```python
# Authenticate with user + password
client = VASTClient(
    user='your_username',
    password='your_password',
    address='vast-vms-hostname'
)

# Generate an API token for a specific user
client.apitokens.post(owner='username')
```

#### View Management

```python
# List all views
for view in client.views.get():
    print(view)

# Create a new view with the default policy
policies = client.viewpolicies.get(name='default')
default_policy = policies[0]  # Get the first (and should be only) matching policy

# Create a new view using the default policy
view = client.views.post(
    path='/prod/pgsql',
    policy_id=default_policy['id'],  # Use the policy's unique identifier
    create_dir=True
)

# Update a view's protocols
view_to_update = client.views.get(path='/prod/pgsql')[0]  # Get the first matching view
updated_view = client.views[view_to_update['id']].patch(protocols=['NFS', 'SMB'])

# Delete a view
client.views[view['id']].delete()
```

#### Snapshot Management

```python
# List snapshots with specific fields
snapshots = client.snapshots.get(fields=['id', 'path'])
for snapshot in snapshots:
    print(f"ID: {snapshot['id']}, Path: {snapshot['path']}")

# Create a new snapshot
snapshot = client.snapshots.post(path='/prod/pgsql', name='db')
```

#### Monitoring

```python
# Query protocol metrics
metrics = client.monitors.ad_hoc_query.get(
    object_type='cluster',
    time_frame='5m',
    prop_list=[
        'ProtoMetrics,proto_name=ProtoCommon,iops',  # Aggregated IOPS across protocols
        'ProtoMetrics,proto_name=ProtoCommon,bw',    # Aggregated bandwidth
        'ProtoMetrics,proto_name=NFS,iops',          # NFS-specific IOPS
        'ProtoMetrics,proto_name=SMB,bw',            # SMB-specific bandwidth
        'ProtoMetrics,proto_name=S3,latency'         # S3 protocol latency
    ]
)
```

### Command Line Interface

The package also includes a CLI tool (`vastpy-cli`) for quick operations.

#### Authentication

Credentials can be provided through environment variables or command-line arguments:

```bash
# Using environment variables
$ export VMS_USER=admin
$ export VMS_PASSWORD=your_password
$ export VMS_ADDRESS=vast-vms-hostname
$ export VMS_TOKEN=token # An optional field supported for Vast versions 5.3 and later
$ export VMS_TENANT_NAME=tenant-name # An optional field, supported for Vast versions 5.3 and later
$ export VMS_API_VERSION=api-version # An optional field, defaults to oldest API

# Or using command-line arguments
$ vastpy-cli --user=admin --password=your_password --address=vast-vms-hostname
```

#### Basic Operations
Any method (get, post, patch, delete) is supported:

```bash
# List snapshots
$ vastpy-cli get snapshots fields=id,path
[
  {
    "path": "/dbs",
    "id": 12
  },
  {
    "path": "/datasets",
    "id": 43
  },
...
]

# Create a new view
$ vastpy-cli post views path=/prod/pgsql create_dir=true policy_id=1
{
  "id": 109,
  "guid": "551b5fc0-42a2-4b77-b385-d5bf6a6c1538",
  "name": "view-109",
  "title": "/prod/pgsql",
...

# Create a new snapshot
$ vastpy-cli post snapshots path=/prod/pgsql name=db
{
  "id": 4707792,
  "name": "db_snapshot",
  "path": "/prod/pgsql"
...

# Delete a view
$ vastpy-cli delete views/109

```

#### Complex Operations

For complex operations, you can use JSON input files:

```bash
# Create a file with your configuration
$ cat > config.json << EOF
{
  "read_access_users": ["vastadmin"],
  "read_access_users_groups": ["vastadmin"],
  "protocols_audit": {
    "log_full_path": true,
    "modify_data_md": true,
    "create_delete_files_dirs_objects": true
  },
  "enable_vast_db_audit": true
}
EOF

# Apply the configuration
vastpy-cli patch clusters/<cluster_id>/auditing --file-input config.json
```

## API Documentation

While developing applications using the VMS API, please refer to the documentation available on your VAST system:
```
https://vast-vms-hostname/docs
```

## Version Compatibility

This SDK is designed to be schema-less, making it compatible with all VAST versions. The Python objects are translated directly to REST API endpoints:

- `client.collection[object].get()` → `GET /api/collection/object`
- `client.collection.post()` → `POST /api/collection`
- `client.collection[object].patch()` → `PATCH /api/collection/object`
- `client.collection[object].delete()` → `DELETE /api/collection/object`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
