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
    def __init__(self, id, height, price=None):
        self.id = id
        self.height = height
        self.devices = []

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


def create_device_with_ports(router_num, port_num, type_name, racks, device_type_id, device_role_id, device_price):
    device_list = []
    for id in range(router_num):
        device_name = type_name + str(id + 1)
        rack = find_free_rack(racks)
        new_device_id = client.create_device(name=device_name, type_id=device_type_id, role_id=device_role_id,
                                             site_id=site_id, rack_id=rack.id, rack_position=rack.empty_position())
        interfaces = []
        for int_id in range(port_num):
            int_name = device_name + "int" + str(int_id + 1)
            interface_id = client.create_interface(name=int_name, device_id=new_device_id)
            interfaces.append(Interface(interface_id))
        device = Device(new_device_id, interfaces, rack=rack, price=device_price)
        rack.add_device(device)
        device_list.append(device)
    return device_list


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


def join_core_with_aggregation(core_routers, aggregation_switches):
    cable_list = []

    for id, agg_r in enumerate(aggregation_switches):
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


def join_aggregation_with_edge(aggregation_switches, edge_switches, pod_number):
    cable_list = []
    
    aggregation_per_pod = len(aggregation_switches) // pod_number
    edge_per_pod = len(edge_switches) // pod_number

    for pod_id in range(pod_number):
        aggregation_start = pod_id * aggregation_per_pod
        aggregation_end = (pod_id + 1) * aggregation_per_pod

        edge_start = pod_id * edge_per_pod
        edge_end = (pod_id + 1) * edge_per_pod

        aggregation_pod_routers = aggregation_switches[aggregation_start:aggregation_end]
        edge_pod_routers = edge_switches[edge_start:edge_end]

        for agg_r in aggregation_pod_routers:
            for edge_r in edge_pod_routers:
                cable_list.append(
                    join_devices(agg_r, edge_r, distance_between_racks=Distances.aggregation_to_edge)
                )
        
    return cable_list


def join_edge_with_hosts(edge_switches, host_list):
    cable_list = []

    hosts_per_router = len(host_list) // len(edge_switches)
    for id, edge_r in enumerate(edge_switches):
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
    PORTS_PER_SWITCH = config["ports_per_switch"]

    HOST_NUMBER = config["host_number"]
    RACK_HEIGHT = config["rack_height"]

    ROUTER_PRICE = Prices.router_price
    SWITCH_PRICE = Prices.switch_price

    POD_NUMBER = int(math.ceil(HOST_NUMBER / (2 * (PORTS_PER_SWITCH - 2))))
    AGGREGATION_NUMBER = 2 * POD_NUMBER
    EDGE_NUMBER = 2 * POD_NUMBER
    DEVICES_NUMBER = CORE_NUMBER + AGGREGATION_NUMBER + EDGE_NUMBER + HOST_NUMBER
    RACK_NUMBER = int(math.ceil(DEVICES_NUMBER / RACK_HEIGHT))

    racks = create_racks(rack_num=RACK_NUMBER, rack_height_U=RACK_HEIGHT, site_id=site_id)

    # CORE ROUTERS
    CORE_PORTS = POD_NUMBER
    # TODO: check if there is not too many pods for PORTS_PER_ROUTER
    core_routers = create_device_with_ports(CORE_NUMBER, CORE_PORTS, "core_router_", racks, router_device_type,
                                            router_role_id, ROUTER_PRICE)

    # AGGREGATION ROUTERS
    AGGREGATION_PORTS = CORE_NUMBER // 2 + EDGE_NUMBER // POD_NUMBER
    aggregation_switches = create_device_with_ports(AGGREGATION_NUMBER, AGGREGATION_PORTS, "aggregation_switch_", racks,
                                                   switch_device_type, switch_role_id, SWITCH_PRICE)

    # EDGE ROUTERS
    EDGE_PORTS = AGGREGATION_NUMBER // POD_NUMBER + HOST_NUMBER // EDGE_NUMBER
    edge_switches = create_device_with_ports(EDGE_NUMBER, EDGE_PORTS, "edge_switch_", racks, switch_device_type,
                                            switch_role_id, SWITCH_PRICE)

    # HOSTS
    host_list = create_hosts(HOST_NUMBER, racks)

    # JOINING PARTY
    cable_list = []

    cable_list += join_core_with_aggregation(core_routers, aggregation_switches)
    cable_list += join_aggregation_with_edge(aggregation_switches, edge_switches, POD_NUMBER)
    cable_list += join_edge_with_hosts(edge_switches, host_list)

    # PRINT
    printCostTable({
        "racks": racks,
        "core_routers": core_routers,
        "aggregation_switches": aggregation_switches,
        "edge_switches": edge_switches,
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
    print("Total cost: ", round(sum([value['price'] for value in grouppedData.values()]), 2))


# create netbox client
client = NetboxClient()
client.auth()

cleanup()

# setup project
client.create_custom_field('price', 'decimal', ["dcim.cable", "dcim.devicetype"])

site_id = client.create_site(name="site")
manufacturer_id_cisco = client.create_manufacturer(name="cisco")
manufacturer_id_dell = client.create_manufacturer(name="Dell")
manufacturer_id_mikrotik = client.create_manufacturer(name="mikrotik")
switch_device_type = client.create_device_type(name="switch", manufacturer_id=manufacturer_id_cisco, model_name="Cisco ASR 9000 Series")
router_device_type = client.create_device_type(name="router", manufacturer_id=manufacturer_id_mikrotik, model_name="Mikrotik CCR1036-8G-2S+EM")
host_device_type = client.create_device_type(name="host", manufacturer_id=manufacturer_id_dell, model_name="PowerEdge R450 XS", price=Prices.dell_poweredge_r450_xs)
switch_role_id = client.create_device_role(name="switch_role")
router_role_id = client.create_device_role(name="router_role")
host_role_id = client.create_device_role(name="host_role")

create_topology(site_id)
