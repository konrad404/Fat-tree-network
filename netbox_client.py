import requests
import json

NETBOX_HOST = "http://localhost:8000"


class NetboxClient:
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json; indent=4"
        }

    def auth(self):
        with open('credentials.json') as file:
            credentials = json.load(file)

        body = {
            "username": credentials["username"],
            "password": credentials["password"]
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/users/tokens/provision/", body)
        api_token = response.json()['display']
        self.headers["Authorization"] = f"Token {api_token}"

    def create_custom_field(self, name, field_type, content_types):
        custom_field = {
            "name": name,
            "type": field_type,
            "content_types": content_types
        }

        self.send_request("POST", f"{NETBOX_HOST}/api/extras/custom-fields/", body=custom_field)


    def create_site(self, name):
        site = {
            "name": name,
            "slug": name
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/sites/", body=site)

        device_id = response.json()["id"]
        print(f"Site {name} with id {device_id} created")
        return device_id

    def get_custom_types_ids(self):
        response = self.send_request("GET", f"{NETBOX_HOST}/api/extras/custom-fields/", body=None)

        custom_types = response.json()["results"]
        return self.get_ids_from_get_response(custom_types)
    
    def get_sites_ids(self):
        response = self.send_request("GET", f"{NETBOX_HOST}/api/dcim/sites/", body=None)

        sites = response.json()["results"]
        return self.get_ids_from_get_response(sites)

    def delete_custom_types(self):
        custom_types = self.get_custom_types_ids()

        for custom_type_id in custom_types:
            self.send_request("DELETE", f"{NETBOX_HOST}/api/extras/custom-fields/{custom_type_id}", body=None)
            print(f"Custom type with id {custom_type_id} deleted")
    
    def delete_sites(self):
        sites = self.get_sites_ids()

        for site_id in sites:
            self.send_request("DELETE", f"{NETBOX_HOST}/api/dcim/sites/{site_id}", body=None)
            print(f"Site with id {site_id} deleted")

    def create_manufacturer(self, name):
        manufacturer = {
            "name": name,
            "slug": name
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/manufacturers/", body=manufacturer)

        manufacturer_id = response.json()["id"]
        print(f"Manufacturer {name} with id {manufacturer_id} created")
        return manufacturer_id

    def get_manufacturers_ids(self):
        response = self.send_request("GET", f"{NETBOX_HOST}/api/dcim/manufacturers/", body=None)

        manufacturers = response.json()["results"]
        return self.get_ids_from_get_response(manufacturers)

    def delete_manufacturers(self):
        manufacturers = self.get_manufacturers_ids()

        for manufacturer_id in manufacturers:
            self.send_request("DELETE", f"{NETBOX_HOST}/api/dcim/manufacturers/{manufacturer_id}", body=None)
            print(f"Manufacturer with id {manufacturer_id} deleted")

    def create_device_type(self, name, manufacturer_id, model_name, price = 0):
        device_type = {
            "name": name,
            "manufacturer": manufacturer_id,
            "model": model_name,
            "slug": name,
            "custom_fields": {
                "price": price,
            },
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/device-types/", body=device_type)

        device_type_id = response.json()["id"]
        print(f"Device type {name} with id {device_type_id} created")
        return device_type_id

    def get_device_types_ids(self):
        response = self.send_request("GET", f"{NETBOX_HOST}/api/dcim/device-types/", body=None)

        device_types = response.json()["results"]
        return self.get_ids_from_get_response(device_types)

    def delete_device_types(self):
        device_types = self.get_device_types_ids()

        for device_type_id in device_types:
            self.send_request("DELETE", f"{NETBOX_HOST}/api/dcim/device-types/{device_type_id}", body=None)
            print(f"Device type with id {device_type_id} deleted")

    def create_rack(self, name, device_number, site_id):
        rack = {
            "site": site_id,
            "name": name,
            "u_height": device_number
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/racks/", body=rack)

        rack_id = response.json()["id"]
        print(f"Rack {name} with id {rack_id} created")
        return rack

    def get_racks_ids(self):
        response = self.send_request("GET", f"{NETBOX_HOST}/api/dcim/racks/", body=None)

        racks = response.json()["results"]
        return self.get_ids_from_get_response(racks)

    def delete_racks(self):
        racks = self.get_racks_ids()

        for rack_id in racks:
            self.send_request("DELETE", f"{NETBOX_HOST}/api/dcim/racks/{rack_id}", body=None)
            print(f"Rack with id {rack_id} deleted")

    def create_device_role(self, name):
        device_role = {
            "name": name,
            "slug": name
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/device-roles/", body=device_role)

        device_role_id = response.json()["id"]
        print(f"Device role {name} with id {device_role_id} created")
        return device_role_id

    def get_device_roles_ids(self):
        response = self.send_request("GET", f"{NETBOX_HOST}/api/dcim/device-roles/", body=None)

        device_roles = response.json()["results"]
        return self.get_ids_from_get_response(device_roles)

    def delete_device_roles(self):
        device_roles = self.get_device_roles_ids()

        for device_role_id in device_roles:
            self.send_request("DELETE", f"{NETBOX_HOST}/api/dcim/device-roles/{device_role_id}", body=None)
            print(f"Device role with id {device_role_id} deleted")

    def create_device(self, name, type_id, role_id, site_id, rack_id, rack_position):
        device = {
            "name": name,
            "device_type": type_id,
            "device_role": role_id,
            "site": site_id,
            "rack": rack_id,
            "position": rack_position,
            "face": "front"
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/devices/", body=device)

        device_id = response.json()["id"]
        print(f"Device {name} with id {device_id} created")
        return device_id

    def get_devices_ids(self):
        response = self.send_request("GET", f"{NETBOX_HOST}/api/dcim/devices/", body=None)

        devices = response.json()["results"]
        return self.get_ids_from_get_response(devices)

    def delete_devices(self):
        devices_ids = self.get_devices_ids()

        for id in devices_ids:
            self.delete_device(id)

    def delete_device(self, device_id):
        self.send_request("DELETE", f"{NETBOX_HOST}/api/dcim/devices/{device_id}", body=None)

        print(f"Device with id {device_id} deleted")

    def create_interface(self, name, device_id):
        interface = {
            "name": name,
            "type": "1000base-t",
            "device": device_id,
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/interfaces/", body=interface)

        interface_id = response.json()["id"]
        print(f"Interface {name} with id {interface_id} created")
        return interface_id

    def create_cable(self, int1_id, int2_id, length = None, price = None):
        cable = {
            "a_terminations": [
                {
                    "object_type": "dcim.interface",
                    "object_id": int1_id,
                },
            ],
            "b_terminations": [
                {
                    "object_type": "dcim.interface",
                    "object_id": int2_id,
                },
            ],
            "status": "connected",
            "length": length,
            "length_unit": "m",
            "custom_fields": {
                "price": price,
            },
        }
        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/cables/", body=cable)

        cable_id = response.json()["id"]
        print(f"Cable for interfaces {int1_id} and {int2_id} with id {cable_id} created")
        return cable_id

    def send_request(self, method, url, body):
        if method == "POST":
            response = requests.post(url, headers=self.headers, json=body)
        elif method == "GET":
            response = requests.get(url, headers=self.headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=self.headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        if response.status_code >= 400:
            print(f"Error {response.status_code} while sending {method} request to {url}: {response.text}")
            return
        return response

    @staticmethod
    def get_ids_from_get_response(items):
        id_list = []
        for item in items:
            id_list.append(item['id'])
        return id_list
