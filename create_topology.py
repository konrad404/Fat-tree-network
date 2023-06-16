from netbox_client import NetboxClient

#create netbox client
client = NetboxClient()
client.auth()

#setup project
# site_id = client.create_site(name="site")
site_id = 1
# manufacturer_id = client.create_manufacturer(name="cisco")
manufacturer_id = 1
# router_device_type = client.create_device_type(name="router", manufacturer_id=manufacturer_id, model_name="cool_model")
router_device_type = 1
# host_device_type = client.create_device_type(name="host", manufacturer_id=manufacturer_id, model_name="cool_model")
host_device_type = 1
# router_role_id = client.create_device_role(name="router_role")
router_role_id = 2
# host_role_id = client.create_device_role(name="host_role")
host_role_id  = 2





#create devices
# router_id = client.create_device(name="router", type_id=router_device_type, role_id=router_role_id, site_id=site_id)
# host_id = client.create_device(name="host", type_id=host_device_type, role_id=host_role_id, site_id=site_id)
#
#
# #that is how you connect 2 devices
# interface_id = client.create_interface(name="int1", device_id=router_id)
# interface2_id = client.create_interface(name="int2", device_id=host_id)
# cable_id = client.create_cable(interface_id, interface2_id)

class Interface:
    def __init__(self, id, is_open=True):
        self.id = id
        self.is_open = is_open

class Device:
    def __init__(self, id, interfaces = []):
        self.id = id
        self.interfaces = interfaces
    def add_interface(self, interface):
        self.interfaces.append(interface)
    def find_first_open_interface(self):
        for interface in self.interfaces:
            if interface.is_open:
                return interface

def create_routers_with_ports(router_num, port_num, type_name):
    router_list = []
    for id in range(router_num):
        router_name = type_name + "_router_" + str(id+1)
        new_router_id = client.create_device(name=router_name, type_id=router_device_type, role_id=router_role_id, site_id=site_id)
        interfaces = []
        for int_id in range(port_num):
            int_name = router_name + "int" + str(int_id+1)
            interface_id = client.create_interface(name=int_name, device_id=new_router_id)
            interfaces.append(Interface(interface_id))
        router_list.append(Device(new_router_id, interfaces))
    return router_list

def create_hosts(host_num):
    host_list = []
    for id in range(host_num):
        host_name = "host" +  str(id+1)
        new_host_id = client.create_device(name=host_name, type_id=host_device_type, role_id=host_role_id, site_id=site_id)
        int_name = host_name + "int" + str(1)
        interface_id = client.create_interface(name=int_name, device_id=new_host_id)
        host_list.append(Device(new_host_id, [Interface(interface_id)]))
    return host_list

def join_devices(left_router, right_router):
    left_interface = left_router.find_first_open_interface()
    right_interface = right_router.find_first_open_interface()
    cable_id = client.create_cable(left_interface.id, right_interface.id)
    left_interface.is_open = False
    right_interface.is_open = False

def join_core_with_aggregation(core_routers, aggregation_routers):
    for id, agg_r in enumerate(aggregation_routers):
        if id%2 == 0:
            core_routers_to_join = core_routers[:len(core_routers) // 2]
            for core_router in core_routers_to_join:
                join_devices(agg_r, core_router)
        else:
            core_routers_to_join = core_routers[len(core_routers) // 2:]
            for core_router in core_routers_to_join:
                join_devices(agg_r, core_router)

def join_aggregation_with_edge(aggregation_routers, edge_routers):
    for agg_r in aggregation_routers:
        for edge_r in edge_routers:
            join_devices(agg_r, edge_r)

# def join_edge_with_hosts()


def create_topology():
    CORE_NUMBER = 4
    AGGREGATION_NUMBER = 8
    EDGE_NUMBER = 8
    POD_NUMBER = 4
    HOST_NUMBER = 16

    # CORE ROUTERS
    CORE_PORTS = AGGREGATION_NUMBER//2
    core_routers = create_routers_with_ports(CORE_NUMBER, CORE_PORTS, "core")
    print(core_routers)

    # AGGREGATION ROUTERS
    AGGREGATION_PORTS = CORE_NUMBER//2 + EDGE_NUMBER//POD_NUMBER
    aggregation_routers = create_routers_with_ports(AGGREGATION_NUMBER, AGGREGATION_PORTS, "aggregation")
    print(aggregation_routers)

    # EDGE ROUTERS
    EDGE_PORTS = AGGREGATION_NUMBER//POD_NUMBER + HOST_NUMBER//EDGE_NUMBER
    edge_routers = create_routers_with_ports(EDGE_NUMBER, EDGE_PORTS, "edge")
    print(edge_routers)

    # HOSTS
    host_list = create_hosts(HOST_NUMBER)
    print(host_list)

    #JOINING PARTY
    join_core_with_aggregation(core_routers, aggregation_routers)

create_topology()




