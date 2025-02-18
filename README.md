
VASTPY
======

This package is a Python SDK to the VMS (VAST Management System) REST API.

While developing against the VMS API use the documentation locally available at https://vms-host-name/docs.

Install
-------

```bash
pip install vastpy
```

The package is hosted in PyPI: https://pypi.org/project/vastpy/

SDK Usage
---------

Initialization:

```python
from vastpy import VASTClient

client = VASTClient(user='user', password='********', address='vast-vms')
```

The API is straightforward:

```python
client.<collection>.get()
client.<collection>.post()
client.<collection>[<object>].get()
client.<collection>[<object>].patch()
client.<collection>[<object>].delete()
```

Accessing collections:

```python
for view in client.views.get():
    print(view)
```

Creating objects:

```python
policy, = client.viewpolicies.get(name='default')

view = client.views.post(path='/prod/pgsql', policy_id=policy['id'], create_dir=True)
```

Modifying/deleting objects:

```python
view, = client.views.get(path='/prod/pgsql')

view = client.views[view['id']].patch(protocols=['NFS', 'SMB'])

client.views[view['id']].delete()
```

Reading metrics:

```python

client.monitors.ad_hoc_query.get(object_type='cluster',
                                 time_frame='5m',
				 prop_list=['ProtoMetrics,proto_name=ProtoCommon,iops',
				            'ProtoMetrics,proto_name=ProtoCommon,bw'])

```

CLI Usage
---------

Credentials can be passed through environment variables or parameters:

```bash

$ export VMS_USER=admin VMS_PASSWORD=******** VMS_ADDRESS=vast-file-server

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

$ vastpy-cli --user=admin --password==******** --address=vast-file-server get snapshots fields=id,path

```

Any method (get, post, patch, delete) is supported:

```bash

$ vastpy-cli post snapshots path=/projects/db name=db
{
  "id": 4707792,
  "name": "db_snapshot",
  "path": "/projects/db"
...

$ vastpy-cli post views path=/projects/db create_dir=true policy_id=1
{
  "id": 109,
  "guid": "551b5fc0-42a2-4b77-b385-d5bf6a6c1538",
  "name": "view-109",
  "title": "/projects/db",
...

$ vastpy-cli delete views/109

```

Accepts JSON file input (`--file-input <JSON_file>`):

```bash

$ cat input.json
{
  "read_access_users": [
    "vastadmin"
  ],
  "read_access_users_groups": [
    "vastadmin"
  ],
  "protocols_audit": {
    "log_full_path": true,
    "modify_data_md": true,
    "create_delete_files_dirs_objects": true
  },
  "enable_vast_db_audit": true
}

$ vastpy-cli patch clusters/<cluster_id>/auditing --file-input input.json
```

Version Compatibility
---------------------

This package is compatible with any VAST version as it's schema-less.

Python objects are simply translated to URLs: `client.collection[object].get()` is translated to `GET /api/collection/object`.
