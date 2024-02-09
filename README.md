# netbox-aws-ipam
Import AWS IP data into NetBox

This script will create a NetBox Tenant for each AWS account in the organization.
A Netbox VRF is created for each VPC in an AWS account.
Netbox Prefixes and IP addresses are added for each VRF/VPC.

Run without the commit flag to view the changes that will be made.

## Installation

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

## Usage

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

## Run from Kriten

Add the runner:
```
{
    "branch": "main",
    "gitURL": "https://github.com/evolvere-tech/netbox-aws-ipam.git",
    "image": "evolvere/netbox-aws-ipam:v0.1",
    "name": "netbox-aws-ipam-runner"
}
```

Add the tasks:
```
 {
     "command": "python netbox_ipam.py config.yaml --commit", 
     "name": "netbox-aws-ipam-commit",
     "runner": "netbox-aws-ipam-runner",
     "synchronous": false,
     "secret": {
         "aws_access_key": "",
         "aws_secret_key": "",
         "netbox_api_token": ""
     }
 }
```

Add another task without the --commit flag to check without applying changes to netbox.

## TODO
Replace the config file with extra_vars sent to the job.


