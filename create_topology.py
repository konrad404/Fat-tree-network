import math
import json

from netbox_client import NetboxClient
from prices import Prices
from distances import Distances


class EntryWithPrice:
    def __init__(self, price=0, name=None, description=None):
        self.price = price
        self.name = name
        self.description = description

    def price_list_entry(self):
        if self.description is None:
            return f"{self.name}: {self.price}"
        return f"{self.name} ({self.description}): {self.price}"


class Interface:
    def __init__(self, id, is_open=True):
        self.id = id
        self.is_open = is_open


class Device(EntryWithPrice):
    def __init__(self, id, interfaces, rack=None, price=0):
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

    def get_rack(self):
        return self.rack

    def get_rack_id(self):
        if self.rack is not None:
            return self.rack.id
        return None



class Cable(EntryWithPrice):
    def __init__(self, id, cable_type, length, price_per_meter, price):
        self.id = id
        self.cableType = cable_type
        self.length = length
        self.pricePerMeter = price_per_meter

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


def create_racks(rack_num, rack_height_u):
    rack_list = []
    for id in range(rack_num):
        rack_name = "rack_" + str(id)
        new_rack_id = client.create_rack(rack_name, device_number=rack_height_u, site_id=site_id)
        rack_list.append(Rack(new_rack_id, rack_height_u))
    return rack_list


def find_free_rack(racks):
    for rack in racks:
        if rack.has_place():
            return rack


def create_device_with_ports(switch_num, port_num, type_name, racks, device_type_id, device_role_id, device_price):
    device_list = []
    for id in range(switch_num):
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


def join_devices(left_device, right_device, distance_between_racks=10):
    left_interface = left_device.find_first_open_interface()
    right_interface = right_device.find_first_open_interface()

    # check if both devices are in the same rack id
    if left_device.get_rack_id() == right_device.get_rack_id():
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


def join_core_with_aggregation(core_switches, aggregation_switches):
    cable_list = []

    for id, agg_r in enumerate(aggregation_switches):
        if id % 2 == 0:
            core_switches_to_join = core_switches[:len(core_switches) // 2]
            for core_switch in core_switches_to_join:
                cable_list.append(
                    join_devices(agg_r, core_switch, distance_between_racks=Distances.core_to_aggregation)
                )
        else:
            core_switches_to_join = core_switches[len(core_switches) // 2:]
            for core_switch in core_switches_to_join:
                cable_list.append(
                    join_devices(agg_r, core_switch, distance_between_racks=Distances.core_to_aggregation)
                )

    return cable_list

def join_core_with_edge(core_switches, edge_switches, pod_number):
    cable_list = []

    edge_per_pod = len(edge_switches) // pod_number

    for pod_id in range(pod_number):
        edge_start = pod_id * edge_per_pod

        for i in range(len(core_switches)):
            edge_switch_to_join = edge_switches[edge_start + i%(edge_per_pod)]
            core_switch_to_join = core_switches[i]
            cable_list.append(
                join_devices(core_switch_to_join, edge_switch_to_join, distance_between_racks=Distances.core_to_edge)
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

        aggregation_pod_switches = aggregation_switches[aggregation_start:aggregation_end]
        edge_pod_switches = edge_switches[edge_start:edge_end]

        for agg_r in aggregation_pod_switches:
            for edge_r in edge_pod_switches:
                cable_list.append(
                    join_devices(agg_r, edge_r, distance_between_racks=Distances.aggregation_to_edge)
                )

    return cable_list


def join_edge_with_hosts(edge_switches, host_list):
    cable_list = []

    hosts_per_switch = len(host_list) // len(edge_switches)
    for id, edge_r in enumerate(edge_switches):
        for host in host_list[id * hosts_per_switch: (id * hosts_per_switch) + hosts_per_switch]:
            cable_list.append(
                join_devices(edge_r, host, distance_between_racks=Distances.edge_to_host)
            )

    return cable_list


def create_topology():
    config_file = open("L2_config.json")
    # config_file = open("L3_config.json")
    config = json.load(config_file)

    TREE_LEVEL = config["tree_level"]
    PORTS_PER_SWITCH = config["ports_per_switch"]

    RACK_HEIGHT = config["rack_height"]


    CORE_NUMBER = pow(PORTS_PER_SWITCH // 2, TREE_LEVEL - 1)
    HOST_NUMBER = 2 * pow(PORTS_PER_SWITCH // 2, TREE_LEVEL)
    EDGE_NUMBER = 2 * CORE_NUMBER
    TOTAL_SWITCHES = (2 * TREE_LEVEL - 1) * CORE_NUMBER
    AGGREGATION_NUMBER = EDGE_NUMBER if TREE_LEVEL == 3 else 0
    POD_SIZE = config["pod_size"]

    SWITCH_PRICE = Prices.switch_price

    if TREE_LEVEL == 2:
        POD_NUMBER = int(EDGE_NUMBER // POD_SIZE)
    elif TREE_LEVEL == 3:
        POD_NUMBER = int(EDGE_NUMBER // (POD_SIZE / 2))

    DEVICES_NUMBER = TOTAL_SWITCHES + HOST_NUMBER
    RACK_NUMBER = int(math.ceil(DEVICES_NUMBER / RACK_HEIGHT))

    racks = create_racks(rack_num=RACK_NUMBER, rack_height_u=RACK_HEIGHT)

    # CORE switches
    core_switches = create_device_with_ports(CORE_NUMBER, PORTS_PER_SWITCH, "core_switch_", racks, switch_device_type,
                                             switch_role_id, SWITCH_PRICE)

    # AGGREGATION switches
    aggregation_switches = create_device_with_ports(AGGREGATION_NUMBER, PORTS_PER_SWITCH, "aggregation_switch_", racks,
                                                    switch_device_type, switch_role_id, SWITCH_PRICE)

    # EDGE switches
    edge_switches = create_device_with_ports(EDGE_NUMBER, PORTS_PER_SWITCH, "edge_switch_", racks, switch_device_type,
                                             switch_role_id, SWITCH_PRICE)

    # HOSTS
    host_list = create_hosts(HOST_NUMBER, racks)

    # JOINING PARTY
    cable_list = []
    
    if TREE_LEVEL == 2:
        cable_list += join_core_with_edge(core_switches, edge_switches, POD_SIZE)
    else:
        cable_list += join_core_with_aggregation(core_switches, aggregation_switches)
        cable_list += join_aggregation_with_edge(aggregation_switches, edge_switches, POD_NUMBER)
    
    cable_list += join_edge_with_hosts(edge_switches, host_list)

    # PRINT
    cost_table_entities = {
        "racks": racks,
        "core_switches": core_switches,
        "aggregation_switches": aggregation_switches,
        "edge_switches": edge_switches,
        "hosts": host_list,
        "cables": cable_list,
    }

    if TREE_LEVEL == 2:
        cost_table_entities.pop("aggregation_switches")

    print_cost_table(cost_table_entities)


def cleanup():
    client.delete_custom_types()
    client.delete_devices()
    client.delete_racks()
    client.delete_device_types()
    client.delete_device_roles()
    client.delete_manufacturers()
    client.delete_sites()


def print_cost_table(entries):
    grouped_data = {}

    for key, value in entries.items():
        print("=" * 20)
        print(key)
        print("-" * 20)

        grouped_data[key] = {
            'price': 0,
            'count': 0,
        }

        for entry in value:
            print(entry.price_list_entry())

            grouped_data[key]['pricePerUnit'] = entry.price
            grouped_data[key]['price'] = grouped_data[key].get('price', 0) + entry.price
            grouped_data[key]['count'] = grouped_data[key].get('count', 0) + 1

        print("\n")

    print("=" * 20)
    print("Summary:")

    for key, value in grouped_data.items():
        if key != 'cables':
            print(f"{key}: {value['count']}x {value['pricePerUnit']} = {value['price']}")
        else:
            total_cable_length = {}
            prices_of_cables = {}

            for cable in entries['cables']:
                cable_type = cable.cableType
                prices_of_cables[cable_type] = cable.pricePerMeter

                if cable_type not in total_cable_length:
                    total_cable_length[cable_type] = 0

                total_cable_length[cable_type] = total_cable_length.get(cable_type, 0) + cable.length

            for cable_type, length in total_cable_length.items():
                print(f"{cable_type}: {length}m x {prices_of_cables[cable_type]}")

    print("=" * 20)
    print("Total cost: ", round(sum([value['price'] for value in grouped_data.values()]), 2))


# create netbox client
client = NetboxClient()
client.auth()

cleanup()

# setup project
client.create_custom_field('price', 'decimal', ["dcim.cable", "dcim.devicetype"])

site_id = client.create_site(name="site")
manufacturer_id_cisco = client.create_manufacturer(name="cisco")
manufacturer_id_dell = client.create_manufacturer(name="Dell")
switch_device_type = client.create_device_type(name="switch", manufacturer_id=manufacturer_id_cisco,
                                               model_name="Cisco ASR 9000 Series")
host_device_type = client.create_device_type(name="host", manufacturer_id=manufacturer_id_dell,
                                             model_name="PowerEdge R450 XS", price=Prices.dell_poweredge_r450_xs)
switch_role_id = client.create_device_role(name="switch_role")
host_role_id = client.create_device_role(name="host_role")

create_topology()
