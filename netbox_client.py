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

    def create_site(self, name):
        site = {
            "name": name,
            "slug": name
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/sites/", body=site)

        device_id = response.json()["id"]
        print(f"Site {name} with id {device_id} created")
        return device_id

    def create_manufacturer(self, name):
        manufacturer = {
            "name": name,
            "slug": name
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/manufacturers/", body=manufacturer)

        manufacturer_id = response.json()["id"]
        print(f"Manufacturer {name} with id {manufacturer_id} created")
        return manufacturer_id

    def create_device_type(self, name, manufacturer_id, model_name):
        device_type = {
            "name": name,
            "manufacturer": manufacturer_id,
            "model": model_name,
            "slug": name
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/device-types/", body=device_type)

        device_type_id = response.json()["id"]
        print(f"Device type {name} with id {device_type_id} created")
        return device_type_id

    def create_device_role(self, name):
        device_role = {
            "name": name,
            "slug": name
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/device-roles/", body=device_role)

        device_role_id = response.json()["id"]
        print(f"Device role {name} with id {device_role_id} created")
        return device_role_id

    def create_device(self, name, type_id, role_id, site_id):
        device = {
            "name": name,
            "device_type": type_id,
            "device_role": role_id,
            "site": site_id,
        }

        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/devices/", body=device)

        device_id = response.json()["id"]
        print(f"Device {name} with id {device_id} created")
        return device_id

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

    def create_cable(self, int1_id, int2_id):
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
        }
        response = self.send_request("POST", f"{NETBOX_HOST}/api/dcim/cables/", body=cable)

        cable_id = response.json()["id"]
        print(f"Cable for interfaces {int1_id} and {int2_id} with id {cable_id} created")
        return cable_id

    def send_request(self, method, url, body):
        if method == "POST":
            response = requests.post(url, headers=self.headers, json=body)
        elif method == "DELETE":
            response = requests.delete(url, headers=self.headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        if response.status_code >= 400:
            print(f"Error {response.status_code} while sending {method} request to {url}: {response.text}")
            return
        return response
