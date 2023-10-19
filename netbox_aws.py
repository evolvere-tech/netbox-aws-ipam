import boto3
import yaml
from pprint import pprint

def get_ipam(config_file):

    try:
        with open(config_file, "r") as fh:
            config = yaml.safe_load(fh)
        ROLE_NAME = config["aws"]["role_name"]
        REGIONS = config["aws"]["regions"]
        SECRETS_PATH = config["secrets"]["path"]

    except:
        return {"rc": 1, "error": f"Problem reading {config_file}."}
    
    secret_path = "/etc/secret/"
    # AWS access key
    aws_access_key_file = f"{SECRETS_PATH}aws_access_key"
    try:
        with open(aws_access_key_file, "r") as fh:
            ACCESS_KEY = fh.readline().strip()
    except:
        print(f"Problem reading {aws_access_key_file}.")
    # AWS secret key
    aws_secret_key_file = f"{SECRETS_PATH}aws_secret_key"
    try:
        with open(aws_secret_key_file, "r") as fh:
            SECRET_KEY = fh.readline().strip()
    except:
        print(f"Problem reading {aws_secret_key_file}.")


    if ACCESS_KEY and SECRET_KEY and ROLE_NAME and REGIONS:
        pass
    else:
        return {"rc": 1, "error": f"config.yaml must set values for ACCESS_KEY and SECRET_KEY and ROLE_NAME and REGIONS."}
    
    try:
        sts_client = boto3.client('sts',
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_KEY)

        assumed_role_object = sts_client.assume_role(
                RoleArn="arn:aws:iam::950001092554:role/IPAM_Poller",
                RoleSessionName="IPAM_Poller"
                )

        credentials = assumed_role_object['Credentials']

        org_client = boto3.client('organizations',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
                )

        account_details = org_client.list_accounts()
        accounts = account_details['Accounts']

    except Exception as e:
        return {"rc": 1, "error": str(e)}

    roles = []
    for account in accounts:
        if str(account['Status']) == 'ACTIVE':
            roles.append(f"arn:aws:iam::{str(account['Id'])}:role/{ROLE_NAME}")

    cloud_accounts = []
    cloud_vpcs_account = []
    cloud_subnets_vrf = []
    cloud_hosts_vrf = []

    for role in roles:
        account_number = role.split(':')[4]
        cloud_accounts.append({"name": account_number, "desc": ""})

        assumed_role_object = sts_client.assume_role(
            RoleArn=role,
            RoleSessionName="IPAM_Poller"
            )
        credentials = assumed_role_object['Credentials']

        for region in REGIONS:
            ec2 = boto3.client('ec2',
                    region_name = region,
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                    )
            aws_vpc_data = ec2.describe_vpcs()
            cloud_vpcs = []
            for vpc in aws_vpc_data['Vpcs']:
                vpc_name = ''
                vpc_tags = vpc.get('Tags', [])
                for tag in vpc_tags:
                    if tag.get('Key') == 'Name':
                        vpc_name = tag.get('Value')
                vpc_id = vpc['VpcId']
                vpc_cidr = vpc['CidrBlock']
                cloud_vpcs.append({"name": vpc_id, "desc": vpc_name})
                aws_subnet_data = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                cloud_subnets = [{"name": vpc_cidr, "desc": "VPC CIDR"}]
                cloud_hosts = []
                for subnet in aws_subnet_data['Subnets']:
                    subnet_id = subnet['SubnetId']
                    subnet_cidr_block = subnet['CidrBlock']
                    az = subnet['AvailabilityZone']
                    cloud_subnets.append({"name": subnet_cidr_block, "desc": az})
                    aws_interface_data = ec2.describe_network_interfaces(Filters=[{'Name':'subnet-id', 'Values':[subnet_id]}])
                    #cloud_hosts = []
                    for interface in aws_interface_data['NetworkInterfaces']:
                        # NetBox requires host IPs to have /32 prefix
                        host_cidr = f"{interface['PrivateIpAddress']}/32"
                        cloud_hosts.append({"name": host_cidr, "desc": interface['AvailabilityZone']})
                # Store hosts from all subnets in the vpc in one list item
                if cloud_hosts:
                    cloud_hosts_vrf.append({"account": account_number, "vpc": vpc_id, "hosts": cloud_hosts})
                cloud_subnets_vrf.append({"account": account_number, "vpc": vpc_id, "subnets": cloud_subnets})
            cloud_vpcs_account.append({"account": account_number, "vpcs": cloud_vpcs})
    return {"rc": 0, "accounts": cloud_accounts, "vpcs": cloud_vpcs_account, "subnets": cloud_subnets_vrf, "hosts": cloud_hosts_vrf}

if __name__ == "__main__":
    cloud_data = get_ipam("secrets.yaml")
    if cloud_data["rc"]:
        print(f"ERROR: {cloud_data['error']}")
    else:
        print("Accounts:")
        pprint(cloud_data["accounts"])
        print("VPCs:")
        pprint(cloud_data["vpcs"])
        print("Subnets:")
        pprint(cloud_data["subnets"])
        print("Hosts:")
        pprint(cloud_data["hosts"])
