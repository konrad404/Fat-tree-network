from netbox_client import NetboxClient

class Interface:
    def __init__(self, id, is_open=True):
        self.id = id
        self.is_open = is_open

class Device:
    def __init__(self, id, interfaces):
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
        host_name = "host_" + str(id+1)
        new_host_id = client.create_device(name=host_name, type_id=host_device_type, role_id=host_role_id, site_id=site_id)
        int_name = host_name + "int" + str(1)
        interface_id = client.create_interface(name=int_name, device_id=new_host_id)
        host_list.append(Device(new_host_id, [Interface(interface_id)]))
    return host_list

def join_devices(left_device, right_device):
    left_interface = left_device.find_first_open_interface()
    right_interface = right_device.find_first_open_interface()
    client.create_cable(left_interface.id, right_interface.id)
    left_interface.is_open = False
    right_interface.is_open = False

def join_core_with_aggregation(core_routers, aggregation_routers):
    for id, agg_r in enumerate(aggregation_routers):
        if id % 2 == 0:
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

def join_edge_with_hosts(edge_routers, host_list):
    hosts_per_router = len(host_list) // len(edge_routers)
    for id, edge_r in enumerate(edge_routers):
        for host in host_list[id:id+hosts_per_router]:
            join_devices(edge_r, host)

def create_topology():
    CORE_NUMBER = 4
    AGGREGATION_NUMBER = 8
    EDGE_NUMBER = 8
    POD_NUMBER = 4
    HOST_NUMBER = 16

    # CORE ROUTERS
    CORE_PORTS = AGGREGATION_NUMBER//2
    core_routers = create_routers_with_ports(CORE_NUMBER, CORE_PORTS, "core")

    # AGGREGATION ROUTERS
    AGGREGATION_PORTS = CORE_NUMBER//2 + EDGE_NUMBER//POD_NUMBER
    aggregation_routers = create_routers_with_ports(AGGREGATION_NUMBER, AGGREGATION_PORTS, "aggregation")

    # EDGE ROUTERS
    EDGE_PORTS = AGGREGATION_NUMBER//POD_NUMBER + HOST_NUMBER//EDGE_NUMBER
    edge_routers = create_routers_with_ports(EDGE_NUMBER, EDGE_PORTS, "edge")

    # HOSTS
    host_list = create_hosts(HOST_NUMBER)
    print(host_list)

    #JOINING PARTY
    join_core_with_aggregation(core_routers, aggregation_routers)
    join_aggregation_with_edge(aggregation_routers, edge_routers)
    join_edge_with_hosts(edge_routers, host_list)


#create netbox client
client = NetboxClient()
client.auth()

#setup project
site_id = client.create_site(name="site")
manufacturer_id = client.create_manufacturer(name="cisco")
router_device_type = client.create_device_type(name="router", manufacturer_id=manufacturer_id, model_name="cool_model")
host_device_type = client.create_device_type(name="host", manufacturer_id=manufacturer_id, model_name="cool_model2")
router_role_id = client.create_device_role(name="router_role")
host_role_id = client.create_device_role(name="host_role")


create_topology()
