from netbox_client import NetboxClient

#create netbox client
client = NetboxClient()
client.auth()

#setup project
site_id = client.create_site(name="site")
manufacturer_id = client.create_manufacturer(name="cisco")
router_device_type = client.create_device_type(name="router", manufacturer_id=manufacturer_id, model_name="cool_model")
host_device_type = client.create_device_type(name="host", manufacturer_id=manufacturer_id, model_name="cool_model")
router_role_id = client.create_device_role(name="router_role")
host_role_id = client.create_device_role(name="host_role")


#create devices
router_id = client.create_device(name="router", type_id=router_device_type, role_id=router_role_id, site_id=site_id)
host_id = client.create_device(name="host", type_id=host_device_type, role_id=host_role_id, site_id=site_id)

#that is how you connect 2 devices
interface_id = client.create_interface(name="int1", device_id=router_id)
interface2_id = client.create_interface(name="int2", device_id=host_id)
cable_id = client.create_cable(interface_id, interface2_id)
