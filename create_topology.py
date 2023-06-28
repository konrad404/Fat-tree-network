import math
import json

from netbox_client import NetboxClient
from prices import Prices
from distances import Distances


class EntryWithPrice:
    def __init__(self, price = 0, name = None, description = None):
        self.price = price
        self.name = name
        self.description = description
    
    def priceListEntry(self):
        if self.description is None:
            return f"{self.name}: {self.price}"
        return f"{self.name} ({self.description}): {self.price}"

class Interface:
    def __init__(self, id, is_open=True):
        self.id = id
        self.is_open = is_open


class Device(EntryWithPrice):
    def __init__(self, id, interfaces, rack = None, price = 0):
        self.id = id
        self.interfaces = interfaces
        self.rack = rack
        
        super().__init__(price, f"Device {id}", f"Device with {len(interfaces)} interfaces")

    def add_interface(self, interface):
        self.interfaces.append(interface)

    def find_first_open_interface(self):
        for interface in self.interfaces:
            if interface.is_open:
                return interface
    
    def getRack(self):
        return self.rack
    
    def getRackId(self):
        if self.rack is not None:
            return self.rack.id
        return None

class Cable(EntryWithPrice):
    def __init__(self, id, cableType, length, pricePerMeter, price):
        self.id = id
        self.cableType = cableType
        self.length = length
        self.pricePerMeter = pricePerMeter

        super().__init__(price, f"Cable {id}", f"{length} m")

class Rack(EntryWithPrice):
    def __init__(self, id, height, devices=[], price=None):
        self.id = id
        self.height = height
        self.devices = devices

        if price is None:
            price = Prices.getRackPriceBasedOnHeight(height)

        super().__init__(price, f"Rack with {height} U", f"Rack {id}")

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
        device = Device(new_router_id, interfaces, rack=rack)
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
        device = Device(new_host_id, [Interface(interface_id)], rack=rack, price=Prices.dell_poweredge_r450_xs)
        rack.add_device(device)
        host_list.append(device)
    return host_list


def join_devices(left_device, right_device, distance_between_racks = 10):
    left_interface = left_device.find_first_open_interface()
    right_interface = right_device.find_first_open_interface()

    # check if both devices are in the same rack id
    if left_device.getRackId() == right_device.getRackId():
        cable_length = 1
    else:
        cable_length = distance_between_racks
    
    cable_price_per_meter = Prices.rj45_cat_7
    cable_price = cable_length * cable_price_per_meter

    cable_id = client.create_cable(left_interface.id, right_interface.id, cable_length, cable_price)
    left_interface.is_open = False
    right_interface.is_open = False

    cable = Cable(cable_id, "rj45_cat_7", cable_length, cable_price_per_meter, cable_price)
    return cable


def join_core_with_aggregation(core_routers, aggregation_routers):
    cable_list = []

    for id, agg_r in enumerate(aggregation_routers):
        if id % 2 == 0:
            core_routers_to_join = core_routers[:len(core_routers) // 2]
            for core_router in core_routers_to_join:
                cable_list.append(
                    join_devices(agg_r, core_router, distance_between_racks=Distances.core_to_aggregation)
                )
        else:
            core_routers_to_join = core_routers[len(core_routers) // 2:]
            for core_router in core_routers_to_join:
                cable_list.append(
                    join_devices(agg_r, core_router, distance_between_racks=Distances.core_to_aggregation)
                )
    
    return cable_list


def join_aggregation_with_edge(aggregation_routers, edge_routers, pod_number):
    cable_list = []
    
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
                cable_list.append(
                    join_devices(agg_r, edge_r, distance_between_racks=Distances.aggregation_to_edge)
                )
        
    return cable_list


def join_edge_with_hosts(edge_routers, host_list):
    cable_list = []

    hosts_per_router = len(host_list) // len(edge_routers)
    for id, edge_r in enumerate(edge_routers):
        for host in host_list[id * hosts_per_router: (id * hosts_per_router) + hosts_per_router]:
            cable_list.append(
                join_devices(edge_r, host, distance_between_racks=Distances.edge_to_host)
            )
    
    return cable_list


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
    cable_list = []

    cable_list += join_core_with_aggregation(core_routers, aggregation_routers)
    cable_list += join_aggregation_with_edge(aggregation_routers, edge_routers, POD_NUMBER)
    cable_list += join_edge_with_hosts(edge_routers, host_list)

    # PRINT
    printCostTable({
        "racks": racks,
        "core_routers": core_routers,
        "aggregation_routers": aggregation_routers,
        "edge_routers": edge_routers,
        "hosts": host_list,
        "cables": cable_list,
   })


def cleanup():
    client.delete_custom_types()
    client.delete_devices()
    client.delete_racks()
    client.delete_device_types()
    client.delete_device_roles()
    client.delete_manufacturers()
    client.delete_sites()

def printCostTable(entries):
    grouppedData = {}

    for key, value in entries.items():
        print("=" * 20)
        print(key)
        print("-" * 20)

        grouppedData[key] = {
            'price': 0,
            'count': 0,
        }

        for entry in value:
            print(entry.priceListEntry())

            grouppedData[key]['pricePerUnit'] = entry.price
            grouppedData[key]['price'] = grouppedData[key].get('price', 0) + entry.price
            grouppedData[key]['count'] = grouppedData[key].get('count', 0) + 1
        
        print("\n")
    
    print("=" * 20)
    print("Summary:")

    for key, value in grouppedData.items():
        if key != 'cables':
            print(f"{key}: {value['count']}x {value['pricePerUnit']} = {value['price']}")
        else:
            totalCableLength = {}
            pricesOfCables = {}
            
            for cable in entries['cables']:
                cableType = cable.cableType
                pricesOfCables[cableType] = cable.pricePerMeter
                
                if cableType not in totalCableLength:
                    totalCableLength[cableType] = 0
                
                totalCableLength[cableType] = totalCableLength.get(cableType, 0) + cable.length
            
            for cableType, length in totalCableLength.items():
                print(f"{cableType}: {length}m x {pricesOfCables[cableType]}")

    print("=" * 20)
    print("Total cost: ", sum([value['price'] for value in grouppedData.values()]))


# create netbox client
client = NetboxClient()
client.auth()

cleanup()

# setup project
client.create_custom_field('price', 'decimal', ["dcim.cable", "dcim.devicetype"])

site_id = client.create_site(name="site")
manufacturer_id = client.create_manufacturer(name="cisco")
manufacturer_id_dell = client.create_manufacturer(name="Dell")
router_device_type = client.create_device_type(name="router", manufacturer_id=manufacturer_id, model_name="cool_model")
host_device_type = client.create_device_type(name="host", manufacturer_id=manufacturer_id_dell, model_name="PowerEdge R450 XS", price=Prices.dell_poweredge_r450_xs)
router_role_id = client.create_device_role(name="router_role")
host_role_id = client.create_device_role(name="host_role")

create_topology(site_id)
