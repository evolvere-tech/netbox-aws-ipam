import json
import requests
import yaml
from pprint import pprint

class NetboxObjectList:
    def __init__(self, url, token, netbox_object_type, cloud_objects, **kwargs):
        self.url = url
        self.token = token
        self.headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
            }
        self.netbox_object_type = netbox_object_type
        cloud_object_names = []
        for cloud_object in cloud_objects:
            cloud_object_names.append(cloud_object["name"])
        self.cloud_objects = cloud_object_names
        self.cloud_object_parents = kwargs
        self.add_to_netbox = []

    def __str__(self):
        out = ""
        for name, netbox_object in self.netbox_objects.items():
            out += f"id: {netbox_object.id} name: {name} desc: {netbox_object.desc}\n"
        return f"{self.netbox_object_type}s: \n{out}"

    def __repr__(self):
        netbox_object_list = ""
        for name, netbox_object in self.netbox_objects.items():
            netbox_object_list += f"id: {netbox_object.id} name: {name}\n"
        return f"{self.netbox_object_type}s('{self.url}', '{self.token}', '{self.cloud_objects}', '{self.cloud_object_parent}')"

    def __setitem__(self, name, netbox_object):
        self.netbox_objects[name] = netbox_object

    def check(self):

        nb_object_list = []
        url = f"{self.url}{self.endpoint}{self.options}"
        response = requests.request("GET", url, headers=self.headers)
        results = response.json().get('results')
        # Check that objects retrieved from netbox have expected parent(s)
        if results:
            for nb_object in results:
                good_parents = True
                # print('nb_object:', nb_object)
                for parent_object_type, parent_object in self.cloud_object_parents.items():
                    # Check that object in netbox has the parent key
                    if nb_object.get(parent_object_type):
                        # Check that the parent value is correct
                        if nb_object.get(parent_object_type).get("name") != parent_object:
                            good_parents = False
                    # If it hasn't even got the key, it doesn't have the parent
                    else:
                        good_parents = False
                if good_parents:
                    #for parent_object_type, parent_object in self.cloud_object_parents.items():
                    # Some netbox object don't have a name field, Aggghhh
                    # They seem to have a "display" field.
                    nb_object_name = nb_object.get("display")
                    nb_object_list.append(nb_object_name)
                    nb_object_id = nb_object.get("id")
                    # id is netbox object primary key.
                    # Objects set in the contructor will not have id set.
                    if self.netbox_objects.get(nb_object_name):
                        desc = self.netbox_objects.get(nb_object_name).desc
                        self.__setitem__(nb_object_name, NetboxObject(id=nb_object_id, desc=desc))
                    # Otherwise create a new object and add it to the list
                    else:
                        self.netbox_objects[nb_object_name] = NetboxObject(id=nb_object_id)
        self.compare(nb_object_list)      
        return {"add": self.add_to_netbox, "delete": self.delete_from_netbox, "no_change": self.no_change}

    def compare(self, nb_object_list):
        nb_object_set = set(nb_object_list)
        cloud_object_set = set(self.cloud_objects)
        self.add_to_netbox = list(cloud_object_set.difference(nb_object_set))
        self.delete_from_netbox = list(nb_object_set.difference(cloud_object_set))
        self.no_change = list(nb_object_set.intersection(cloud_object_set))
        return    

    def add(self):
        url = f"{self.url}{self.endpoint}"
        parents = {}
        objects_added = []
        for object_name in self.add_to_netbox:
            object_desc = self.netbox_objects.get(object_name).desc
            payload = {self.netbox_object_primary_key: object_name, "slug": object_name, "description": object_desc}
            for parent_object_type, parent_object in self.cloud_object_parents.items():
                parents.update({parent_object_type: {"name": parent_object}})
            payload.update(parents)
            response = requests.request("POST", url, headers=self.headers, data=json.dumps(payload))
            if response.status_code == 201:
                objects_added.append(object_name)
        if objects_added:
            response_msg = f"{self.netbox_object_plural} {objects_added} added to netbox."
        else:
            response_msg = f"No {self.netbox_object_plural} to add to netbox."
        return response_msg

    def delete(self):
        url = f"{self.url}{self.endpoint}"
        payload_list = []
        for object_name in self.delete_from_netbox:
            object_id = self.netbox_objects.get(object_name).id
            payload = {"id": object_id}
            payload_list.append(payload)
        if payload_list:
            response = requests.request("DELETE", url, headers=self.headers, data=json.dumps(payload_list))
            if response.status_code == 204:
                return f"{self.netbox_object_type}s {self.delete_from_netbox} deleted from netbox."
            else:
                return f"ERROR: deleting {self.netbox_object_plural} {self.delete_from_netbox}: {response.text}."
        else:
            return f"No {self.netbox_object_plural} to delete from netbox."

class NetboxObject:
    # id is not known when object is created, it is read from netbox.
    def __init__(self, id=None, desc=None):
        self.id = id
        self.desc = desc

    def __str__(self):
        return f"id: {self.id} name: {self.name} desc: {self.desc}"

class Tenants(NetboxObjectList):
    def __init__(self, url, token, cloud_objects, **kwargs):
        super().__init__(url, token, "tenant", cloud_objects, **kwargs)      
        self.netbox_objects = {}
        self.netbox_object_type == "tenant"
        self.netbox_object_plural = "tenants"
        self.netbox_object_primary_key = "name"
        self.endpoint = "/api/tenancy/tenants/"
        for cloud_object in cloud_objects:
            self.netbox_objects[cloud_object["name"]] = NetboxObject(desc=cloud_object["desc"])
        # Get tenant-group id to use as a query parameter
        url = f"{self.url}/api/tenancy/tenant-groups/?name=AWS"
        response = requests.request("GET", url, headers=self.headers)
        results = response.json().get('results')
        if results:
            group_id = results[0]["id"]
            self.options = f"?group_id={group_id}"
        else:
            self.options = ""

    def check(self):
        url = f"{self.url}/api/tenancy/tenant-groups/?name=AWS"
        response = requests.request("GET", url, headers=self.headers)
        results = response.json().get('results')
        if not results:
            print("Add Tenant Groups ['AWS']")
        super(Tenants, self).check()
        return {"add": self.add_to_netbox, "delete": self.delete_from_netbox, "no_change": self.no_change}

    def add(self):
        url = f"{self.url}/api/tenancy/tenant-groups/?name=AWS"
        response = requests.request("GET", url, headers=self.headers)
        results = response.json().get('results')
        if not results:
            payload = {"name": "AWS", "slug": "aws", "description": "Imported from AWS"}
            url = f"{self.url}/api/tenancy/tenant-groups/"
            response = requests.request("POST", url, headers=self.headers, data=json.dumps(payload))
        super(Tenants, self).add()


class Vrfs(NetboxObjectList):
    def __init__(self, url, token, cloud_objects, **kwargs):
        super().__init__(url, token, "vrf", cloud_objects, **kwargs)   
        self.netbox_objects = {}
        self.netbox_object_type == "vrf"
        self.netbox_object_plural = "vrfs"
        self.netbox_object_primary_key = "name"
        self.endpoint = "/api/ipam/vrfs/"
        for cloud_object in cloud_objects:
            self.netbox_objects[cloud_object["name"]] = NetboxObject(desc=cloud_object["desc"])
        self.options = f"?tenant={kwargs['tenant']}"

class Prefixes(NetboxObjectList):
    def __init__(self, url, token, cloud_objects, **kwargs):
        super().__init__(url, token, "prefix", cloud_objects, **kwargs)  
        self.netbox_objects = {}
        self.netbox_object_type == "prefix"
        self.netbox_object_plural = "prefixes"
        self.netbox_object_primary_key = "prefix"
        self.endpoint = "/api/ipam/prefixes/"
        for cloud_object in cloud_objects:
            self.netbox_objects[cloud_object["name"]] = NetboxObject(desc=cloud_object["desc"])
        # Get vrf id to use as a query parameter
        url = f"{self.url}/api/ipam/vrfs/?name={kwargs['vrf']}"
        response = requests.request("GET", url, headers=self.headers)
        results = response.json().get('results')
        if results:
            vrf_id = results[0]["id"]
            self.options = f"?vrf_id={vrf_id}"
        else:
            self.options = ""

class IPAddresses(NetboxObjectList):
    def __init__(self, url, token, cloud_objects, **kwargs):
        super().__init__(url, token, "address", cloud_objects, **kwargs)  
        self.netbox_objects = {}
        self.netbox_object_type == "address"
        self.netbox_object_plural = "addresses"
        self.netbox_object_primary_key = "address"
        self.endpoint = "/api/ipam/ip-addresses/"
        for cloud_object in cloud_objects:
            self.netbox_objects[cloud_object["name"]] = NetboxObject(desc=cloud_object["desc"])
        # Get vrf id to use as a query parameter
        url = f"{self.url}/api/ipam/vrfs/?name={kwargs['vrf']}"
        response = requests.request("GET", url, headers=self.headers)
        results = response.json().get('results')
        if results:
            vrf_id = results[0]["id"]
            self.options = f"?vrf_id={vrf_id}"
        else:
            self.options = ""

if __name__ == "__main__":
    test()
