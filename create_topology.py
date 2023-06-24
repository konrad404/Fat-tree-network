import math
import json

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


class Rack:
    def __init__(self, id, height, devices=[]):
        self.id = id
        self.height = height
        self.devices = devices

    def has_place(self):
        return len(self.devices) < self.height

    def empty_position(self):
        return len(self.devices) + 1

    def add_device(self, device):
        self.devices.append(device)


def create_racks(rack_num, rack_height_U, site_id):
    rack_list = []
    for id in range(rack_num):
        rack_name = "rack_" + str(id)
        new_rack_id = client.create_rack(rack_name, device_number=rack_height_U, site_id=site_id)
        rack_list.append(Rack(new_rack_id, rack_height_U))
    return rack_list


def find_free_rack(racks):
    for rack in racks:
        if rack.has_place():
            return rack


def create_routers_with_ports(router_num, port_num, type_name, racks):
    router_list = []
    for id in range(router_num):
        router_name = type_name + "_router_" + str(id + 1)
        rack = find_free_rack(racks)
        new_router_id = client.create_device(name=router_name, type_id=router_device_type, role_id=router_role_id,
                                             site_id=site_id, rack_id=rack.id, rack_position=rack.empty_position())
        interfaces = []
        for int_id in range(port_num):
            int_name = router_name + "int" + str(int_id + 1)
            interface_id = client.create_interface(name=int_name, device_id=new_router_id)
            interfaces.append(Interface(interface_id))
        device = Device(new_router_id, interfaces)
        rack.add_device(device)
        router_list.append(device)
    return router_list


def create_hosts(host_num, racks):
    host_list = []
    for id in range(host_num):
        host_name = "host_" + str(id + 1)
        rack = find_free_rack(racks)
        new_host_id = client.create_device(name=host_name, type_id=host_device_type, role_id=host_role_id,
                                           site_id=site_id, rack_id=rack.id, rack_position=rack.empty_position())
        int_name = host_name + "int" + str(1)
        interface_id = client.create_interface(name=int_name, device_id=new_host_id)
        device = Device(new_host_id, [Interface(interface_id)])
        rack.add_device(device)
        host_list.append(device)
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


def join_aggregation_with_edge(aggregation_routers, edge_routers, pod_number):
    aggregation_per_pod = len(aggregation_routers) // pod_number
    edge_per_pod = len(edge_routers) // pod_number

    for pod_id in range(pod_number):
        aggregation_start = pod_id * aggregation_per_pod
        aggregation_end = (pod_id + 1) * aggregation_per_pod

        edge_start = pod_id * edge_per_pod
        edge_end = (pod_id + 1) * edge_per_pod

        aggregation_pod_routers = aggregation_routers[aggregation_start:aggregation_end]
        edge_pod_routers = edge_routers[edge_start:edge_end]

        for agg_r in aggregation_pod_routers:
            for edge_r in edge_pod_routers:
                join_devices(agg_r, edge_r)


def join_edge_with_hosts(edge_routers, host_list):
    hosts_per_router = len(host_list) // len(edge_routers)
    for id, edge_r in enumerate(edge_routers):
        for host in host_list[id * hosts_per_router: (id * hosts_per_router) + hosts_per_router]:
            join_devices(edge_r, host)


def create_topology(site_id):
    config_file = open("config.json")
    config = json.load(config_file)

    CORE_NUMBER = config["core_router_number"]
    PORTS_PER_ROUTER = config["ports_per_router"]
    HOST_NUMBER = config["host_number"]
    RACK_HEIGHT = config["rack_height"]

    POD_NUMBER = int(math.ceil(HOST_NUMBER / (2 * (PORTS_PER_ROUTER - 2))))
    AGGREGATION_NUMBER = 2 * POD_NUMBER
    EDGE_NUMBER = 2 * POD_NUMBER
    DEVICES_NUMBER = CORE_NUMBER + AGGREGATION_NUMBER + EDGE_NUMBER + HOST_NUMBER
    RACK_NUMBER = int(math.ceil(DEVICES_NUMBER / RACK_HEIGHT))

    racks = create_racks(rack_num=RACK_NUMBER, rack_height_U=RACK_HEIGHT, site_id=site_id)

    # CORE ROUTERS
    CORE_PORTS = AGGREGATION_NUMBER // 2
    # TODO: check if generated number of porst is acceptable (depends on router machine)
    core_routers = create_routers_with_ports(CORE_NUMBER, CORE_PORTS, "core", racks)

    # AGGREGATION ROUTERS
    AGGREGATION_PORTS = CORE_NUMBER // 2 + EDGE_NUMBER // POD_NUMBER
    aggregation_routers = create_routers_with_ports(AGGREGATION_NUMBER, AGGREGATION_PORTS, "aggregation", racks)

    # EDGE ROUTERS
    EDGE_PORTS = AGGREGATION_NUMBER // POD_NUMBER + HOST_NUMBER // EDGE_NUMBER
    edge_routers = create_routers_with_ports(EDGE_NUMBER, EDGE_PORTS, "edge", racks)

    # HOSTS
    host_list = create_hosts(HOST_NUMBER, racks)

    # JOINING PARTY
    join_core_with_aggregation(core_routers, aggregation_routers)
    join_aggregation_with_edge(aggregation_routers, edge_routers, POD_NUMBER)
    join_edge_with_hosts(edge_routers, host_list)


def cleanup():
    client.delete_devices()
    client.delete_racks()
    client.delete_device_types()
    client.delete_device_roles()
    client.delete_manufacturers()
    client.delete_sites()


# create netbox client
client = NetboxClient()
client.auth()

cleanup()

# #setup project
site_id = client.create_site(name="site")
manufacturer_id = client.create_manufacturer(name="cisco")
router_device_type = client.create_device_type(name="router", manufacturer_id=manufacturer_id, model_name="cool_model")
host_device_type = client.create_device_type(name="host", manufacturer_id=manufacturer_id, model_name="cool_model2")
router_role_id = client.create_device_role(name="router_role")
host_role_id = client.create_device_role(name="host_role")

create_topology(site_id)
