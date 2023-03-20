
VASTPY
======

This package is a Python SDK to the VMS (VAST Management System) REST API.
While developing against the VMS API use the documentation locally available at https://<VMS>/docs.

Usage
-----

Initialization:

    from vastpy import VASTClient

    client = VASTClient(user='user', password='********', address='vast-vms')

The API is straightforward:

    client.<collection>.get()
    client.<collection>.post()
    client.<collection>[<object>].get()
    client.<collection>[<object>].patch()
    client.<collection>[<object>].delete()

Accessing collections:

    for view in client.views.get():
        print(view)

Creating objects:

    policy, = client.viewpolicies.get(name='default')

    view = client.views.post(path='/prod/pgsql', policy_id=default['id'], create_dir=True)

Modifying/deleting objects:

    view, = client.views.get(path='/prod/pgsql')

    view = client.views[view['id']].patch(protocols=['NFS', 'SMB'])

    client.views[view['id']].delete()
