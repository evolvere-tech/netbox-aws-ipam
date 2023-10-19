# netbox-aws-ipam
Import AWS IP data into NetBox

This script will create a NetBox Tenant for each AWS account in the organization.
A Netbox VRF is created for each VPC in an AWS account.
Netbox Prefixes and IP addresses are added for each VRF/VPC.

Run without the commit flag to view the changes that will be made.

** Installation

Create a Python3 virtual environment
```
python3 -m venv venv
```

Source the virtual environment
```
source venv/bin/activate
```

Install the requirements
```
pip install -r requirements.txt
```

** Usage

```
usage: netbox_ipam.py [-h] [--commit] config_file

positional arguments:
  config_file  YAML configuration file.

optional arguments:
  -h, --help   show this help message and exit
  --commit     Update the NetBox database.
```

Format of config_file:
```
aws:
  role_name: "IPAM_Poller"
  regions: ["eu-west-1"]

netbox:
  url: "http://192.168.10.55:8000"

secrets:
  path: "/etc/secret/"
```

The script will assume the role ```role_name```. The AWS role must Read, List access to EC2 and Organisations services.

Secret directory should contain three files:
aws_access_key    - Contains AWS access key
aws_secret_key    - Contains AWS secret key
netbox_api_token  - Contains NetBox API token
