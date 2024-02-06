
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

Usage
-----

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

Version Compatibility
---------------------

This package is compatible with any VAST version as it's schema-less.

Python objects are simply translated to URLs: `client.collection[object].get()` is translated to `GET /api/collection/object`.
