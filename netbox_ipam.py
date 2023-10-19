import netbox_aws
from netbox_common import Tenants, Vrfs, Prefixes, IPAddresses
from argparse import ArgumentParser
from pprint import pprint
import yaml
import copy
import sys

parser = ArgumentParser()
parser.add_argument("config_file", help="YAML configuration file.")
parser.add_argument("--commit", help="Update the NetBox database.", action="store_true")
args = parser.parse_args()

try:
    with open(args.config_file, "r") as fh:
        config = yaml.safe_load(fh)
    NETBOX_URL = config["netbox"]["url"]
    SECRETS_PATH = config["secrets"]["path"]

except:
    print(f"Problem reading config.yaml.")

netbox_api_token_file = f"{SECRETS_PATH}netbox_api_token"
try:
    with open(netbox_api_token_file, "r") as fh:
        NETBOX_API_TOKEN = fh.readline().strip()
except:
    print(f"Problem reading {netbox_api_token_file}.")

print("Retrieving IP information from AWS...")
aws_ipam = netbox_aws.get_ipam(args.config_file)
if aws_ipam["rc"]:
    print(f"ERROR: {aws_ipam['error']}")
else:
    print("Processing IP information from AWS...")
    netbox_objects_list = []
    accounts = aws_ipam["accounts"]
    tens = Tenants(NETBOX_URL, NETBOX_API_TOKEN, accounts, group="AWS")
    changes = tens.check()
    if changes["add"] or changes["delete"]:
        netbox_objects_list.append({"netbox_object_type": "Tenants", "changes": copy.copy(changes), "netbox_object": copy.copy(tens)})
    # VPCs/VRFs
    for vpcs in aws_ipam["vpcs"]:
        vrfs = Vrfs(NETBOX_URL, NETBOX_API_TOKEN, vpcs["vpcs"], tenant=vpcs["account"])
        changes = vrfs.check()
        if changes["add"] or changes["delete"]:
            netbox_objects_list.append({"netbox_object_type": "VRFs", "changes": copy.copy(changes), "netbox_object": copy.copy(vrfs)})
    # Subnets/Prefixes
    for subnets in aws_ipam["subnets"]:
        prefs = Prefixes(NETBOX_URL, NETBOX_API_TOKEN, subnets["subnets"], tenant=subnets["account"], vrf=subnets["vpc"])
        changes = prefs.check()
        if changes["add"] or changes["delete"]:
            netbox_objects_list.append({"netbox_object_type": "Prefixes", "changes": copy.copy(changes), "netbox_object": copy.copy(prefs)})
    # Hosts/IP Addresses
    for hosts in aws_ipam["hosts"]:
        addrs = IPAddresses(NETBOX_URL, NETBOX_API_TOKEN, hosts["hosts"], tenant=hosts["account"], vrf=hosts["vpc"])
        changes = addrs.check()
        if changes["add"] or changes["delete"]:
            netbox_objects_list.append({"netbox_object_type": "IP Addresses", "changes": copy.copy(changes), "netbox_object": copy.copy(addrs)})
    if args.commit:
        if netbox_objects_list:
            print("Updating NetBox...")
            for netbox_objects in netbox_objects_list:
                if netbox_objects['changes']['add'] or netbox_objects['changes']['delete']:
                    pass
                else:
                    print("No updates needed.")
            for netbox_objects in netbox_objects_list:
                if netbox_objects['changes']['add']:
                    print(f"Adding {netbox_objects['netbox_object_type']} {netbox_objects['changes']['add']}.")
                    netbox_objects["netbox_object"].add()
            for netbox_objects in reversed(netbox_objects_list):
                if netbox_objects['changes']['delete']:
                    print(f"Deleting {netbox_objects['netbox_object_type']} {netbox_objects['changes']['delete']}.")
                    netbox_objects["netbox_object"].delete()
        else:
            print("No updates needed.")
    else:
        #print("Updates from AWS to NetBox:")
        for netbox_objects in netbox_objects_list:
            if netbox_objects['changes']['add'] or netbox_objects['changes']['delete']:
                if netbox_objects['changes']['add']:
                    print(f"Add {netbox_objects['netbox_object_type']} {netbox_objects['changes']['add']}.")
                if netbox_objects['changes']['delete']:
                    print(f"Delete {netbox_objects['netbox_object_type']} {netbox_objects['changes']['delete']}.")
            else:
                print("No updates needed.")
        if not netbox_objects_list:
            print("No updates needed.")
