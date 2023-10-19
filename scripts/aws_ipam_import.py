from django.utils.text import slugify
from django.forms import PasswordInput

from dcim.choices import DeviceStatusChoices, SiteStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from extras.scripts import *

import requests
import json


class AWSIPAM(Script):

    class Meta:
        name = "AWS IPAM Import"
        description = "Import AWS IP allocations"
        commit_default = False
        field_order = ['kriten_url', 'kriten_username', 'kriten_password']

    kriten_url = StringVar(
        description="URL for Kriten task",
        default = "http://kriten.kriten.192.168.10.102.nip.io"
    )
    kriten_username = StringVar(
        description="Kriten username"
    )
    kriten_password = StringVar(
        widget=PasswordInput,
        description="Kriten password"
    )

    def run(self, data, commit):
        # Launch job
        session = requests.Session()
        headers = {
            "Content-Type": "application/json"
        }
        payload = json.dumps({
            "username": data["kriten_username"],
            "password": data["kriten_password"],
            "provider": "local"
        })

        login_url = f"{data['kriten_url']}/api/v1/login"

        if commit:
            launch_url = f"{data['kriten_url']}/api/v1/jobs/netbox-aws-ipam-commit/"
            msg = "Netbox AWS import run in update mode"
        else:
            launch_url = f"{data['kriten_url']}/api/v1/jobs/netbox-aws-ipam-check/"
            msg = "Netbox AWS import run in check mode"

        login = session.post(login_url, headers=headers, data=payload)
        if login.status_code == 200:
            launch = session.post(launch_url, headers=headers)
            if launch.status_code == 200:
                job_id = launch.json()["value"]
                self.log_success(f"Job {job_id} launched")
            else:
                self.log_failure(f"Kriten job launch failed")
        else:
            self.log_failure(f"Kriten job login failed")

        return f"Bosh! {msg}"
