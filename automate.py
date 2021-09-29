""" Copyright (c) 2021 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
           https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

import os, json, requests, urllib3, openpyxl, time
import pandas as pd
from dotenv import load_dotenv

# suppress unverified HTTPS request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# environment variables
load_dotenv()
vmanage_host = os.getenv("VMANAGE_HOST")
vmanage_port = os.getenv("VMANAGE_PORT")
vmanage_username = os.getenv("VMANAGE_USERNAME")
vmanage_password = os.getenv("VMANAGE_PASSWORD")

# define available workflows
workflows = [
    "Commision a new store/branch edge router",
    "Decommission a closed store/branch edge router",
    "Replace (RMA) a broken store/branch edge router",
    "Store reclassification",
    "Configure changes to existing store/branch edge routers"
]

# define available sub-workflows for commission_router
commission_router_subworkflows = [
    "Link templates and get template input variables",
    "Upload data and get config down to routers"
]

# define available sub-workflows for store_reclassification
reclassification_subworkflows = [
    "Specify routers and templates",
    "Upload data and reattach routers"
]

# workflow #1 Commision a new store/branch edge router
def commission_router(auth):
    subworkflow_id = commission_router_menu()
    device_templates = vManage(auth).get_device_templates()
    device_list = vManage(auth).get_device_list()
    if subworkflow_id == 1:
        # sub-workflow #1 Link templates and get template input variables
        mapping, file = load_mapping(1)
        all_template_input = {}
        for row in mapping:
            template_name = row["TemplateName"]
            template_id = next(device_template["templateId"] for device_template in device_templates if device_template["templateName"] == template_name)
            device_chassis_numbers = row["DeviceChassisNumber"].split(",")
            device_id_list = [device["uuid"] for device in device_list if device["chasisNumber"] in device_chassis_numbers]
            template_input_sets = vManage(auth).get_template_input(template_id, device_id_list)
            for template_input_set in template_input_sets:
                template_input_set.pop("csv-status", None)
            write_excel(file, template_name, template_input_sets)

    elif subworkflow_id == 2:
        # sub-workflow #2 Upload data and get config down to routers
        mapping, file = load_mapping(1)
        for row in mapping:
            template_name = row["TemplateName"]
            template_id = next(device_template["templateId"] for device_template in device_templates if device_template["templateName"] == template_name)
            template_input_variables = excel_to_json(file, template_name)
            vManage(auth).attach_template(template_id, template_input_variables)

# workflow #2 Decommission a closed store/branch edge router
def decommission_router(auth):
    # sub-workflow #1 detach the router from template (change to cli mode)
    device_hostname = get_hostname()
    device_list = vManage(auth).get_device_list()
    device_details = next(device for device in device_list if "host-name" in device and device["host-name"] == device_hostname)
    vManage(auth).detach_template(device_details["deviceType"], device_details["uuid"], device_details["deviceIP"])

    # sub-workflow #2 invalidate router certificate
    vManage(auth).invalidate_certificate(device_details["chasisNumber"], device_details["serialNumber"])

    # sub-workflow #3 send to controllers
    vManage(auth).sync_controllers()

# workflow #3 Replace (RMA) a broken store/branch edge router
def rma(auth):
    mapping, file = load_mapping(3)
    device_list = vManage(auth).get_device_list()
    for row in mapping:
        # sub-workflow #1 get old router variables and prepare for new router
        old_device = next(device for device in device_list if device["chasisNumber"] == row["OldDevice"])
        new_device = next(device for device in device_list if device["chasisNumber"] == row["NewDevice"])
        template_input = vManage(auth).get_template_input(old_device["templateId"], [old_device["uuid"]])
        template_input[0].pop("csv-status", None)
        template_input[0]["csv-deviceId"] = new_device["uuid"]

        # sub-workflow #2 remove / decommission old router depending on RMAviaTAC flag)
        if row["RMAviaTAC"] == "Y":
            vManage(auth).invalidate_certificate(old_device["chasisNumber"], old_device["serialNumber"])
            sync_controllers_action = vManage(auth).sync_controllers()
            # NOTE TO CONSIDER IN PRODUCTION: let this action runs for all old devices before checking the status
            # so that this checking of action status does not block the app runtime
            sync_controllers_action_status = "in_progress"
            while not sync_controllers_action_status == "done":
                time.sleep(2)
                sync_controllers_action_status = vManage(auth).track_action_status(sync_controllers_action["id"])
            vManage(auth).completely_remove_device(old_device["uuid"])
        else:
            decommission_router_action = vManage(auth).decommission_device(old_device["uuid"])
            vManage(auth).invalidate_certificate(old_device["chasisNumber"], old_device["serialNumber"])
            sync_controllers_action = vManage(auth).sync_controllers()

        # sub-workflow #3 attach new router to template
        attach_template_action = vManage(auth).attach_template(old_device["templateId"], template_input)

# workflow #4 Store reclassification
def store_reclassification(auth):
    subworkflow_id = reclassification_menu()
    device_templates = vManage(auth).get_device_templates()
    device_list = vManage(auth).get_device_list()
    if subworkflow_id == 1:
        # sub-workflow #1 Specify routers and templates
        mapping, file = load_mapping(4)
        all_template_input = {}
        for row in mapping:
            template_name = row["TemplateName"]
            template_id = next(device_template["templateId"] for device_template in device_templates if device_template["templateName"] == template_name)
            device_chassis_numbers = row["DeviceChassisNumber"].split(",")
            device_id_list = [device["uuid"] for device in device_list if device["chasisNumber"] in device_chassis_numbers]
            template_input_sets = vManage(auth).get_template_input(template_id, device_id_list)
            #print(template_input_sets)
            for template_input_set in template_input_sets:
                template_input_set.pop("csv-status", None)
            write_excel(file, template_name, template_input_sets)

    elif subworkflow_id == 2:
        # sub-workflow #2 Upload data and reattach routers
        mapping, file = load_mapping(4)
        for row in mapping:
            template_name = row["TemplateName"]
            template_id = next(device_template["templateId"] for device_template in device_templates if device_template["templateName"] == template_name)
            template_input_variables = excel_to_json(file, template_name)
            vManage(auth).attach_template(template_id, template_input_variables)

# workflow #5 Configure changes to existing store/branch edge routers
def configure_changes(auth):
    # sub-workflow #1 copy an existing template and make changes
    template_name = get_template_name()
    device_templates = vManage(auth).get_device_templates()
    template_id = next(device_template["templateId"] for device_template in device_templates if device_template["templateName"] == template_name)
    device_template_config = vManage(auth).get_template_config(template_id)
    device_template_config.pop("templateId", None)
    device_template_config["templateName"] += "-Changed"
    device_template_config["templateDescription"] += "-Changed"
    # NOTE: hard coded template changes
    new_feature_template = {
        "templateName": "C8000v-Alvin-Test-SVI-100",
        "templateDescription": "C8000v-Alvin-Test-SVI-100",
        "templateType": "vpn-interface-svi",
        "deviceType": [ "vedge-C8000V" ],
        "factoryDefault": False,
        "templateMinVersion": "15.0.0",
        "configType": "xml",
        "resourceGroup": "global",
        "templateDefinition": {
            "if-name": {
                "vipObjectType": "object",
                "vipType": "variableName",
                "vipValue": "",
                "vipVariableName": "vpn_if_svi_100_if_name"
            },
            "description": {
                "vipObjectType": "object",
                "vipType": "variableName",
                "vipValue": "",
                "vipVariableName": "vpn_if_svi_100_description"
            },
            "ip": {
                "address": {
                    "vipObjectType": "object",
                    "vipType": "variableName",
                    "vipValue": "",
                    "vipVariableName": "vpn_if_svi_100_if_ipv4_prefix"
                }
            },
            "shutdown": {
                "vipObjectType": "object",
                "vipType": "constant",
                "vipValue": "false",
                "vipVariableName": "vpn_if_svi_shutdown"
            }
        }
    }
    new_feature_template_id = vManage(auth).add_feature_template(new_feature_template)
    for template in device_template_config["generalTemplates"]:
        if template["templateType"] == "cisco_vpn" and "subTemplates" in template:
            template["subTemplates"].append({
                "templateId": new_feature_template_id,
                "templateType": "vpn-interface-svi"
            })
    new_device_template_id = vManage(auth).add_device_template(device_template_config)

    # sub-workflow #2 deploy changes to routers in batches
    attached_devices = vManage(auth).get_template_attached_devices(template_id)
    last_octet = 1
    for device in attached_devices:
        template_inputs = vManage(auth).get_template_input(new_device_template_id, [device["uuid"]])
        template_inputs[0].pop("csv-status", None)
        template_inputs[0]["csv-deviceIP"] = f"10.10.119.{last_octet}"
        template_inputs[0]["csv-host-name"] = f"api-test-{last_octet}"
        template_inputs[0]["//system/host-name"] = f"api-test-{last_octet}"
        template_inputs[0]["//system/system-ip"] = f"10.10.119.{last_octet}"
        template_inputs[0]["//system/site-id"] = f"119"
        template_inputs[0]["/0/vpn_if_svi_100_if_name/interface/if-name"] = "Vlan100"
        template_inputs[0]["/0/vpn_if_svi_100_if_name/interface/description"] = f"Changed by API"
        template_inputs[0]["/0/vpn_if_svi_100_if_name/interface/ip/address"] = f"100.100.100.{last_octet}/24"
        vManage(auth).attach_template(new_device_template_id, template_inputs)
        print(f"Deployed changes to {last_octet} device(s)")
        last_octet += 1
        time.sleep(60)

# initiated user selected workflow
def workflow_starter(id):
    auth = vManage(None).authentication()
    if id == 1:
        commission_router(auth)
    elif id == 2:
        decommission_router(auth)
    elif id == 3:
        rma(auth)
    elif id == 4:
        store_reclassification(auth)
    elif id == 5:
        configure_changes(auth)

# display menu for choosing sub-workflow of commission_router
def commission_router_menu():
    print()
    for i in range(len(commission_router_subworkflows)):
        print(f"{i+1}. {commission_router_subworkflows[i]}")
    subworkflow_id = input("Which sub-workflow do you want to start? ")
    return int(subworkflow_id)

# display menu for choosing sub-workflow of store_reclassification
def reclassification_menu():
    print()
    for i in range(len(reclassification_subworkflows)):
        print(f"{i+1}. {reclassification_subworkflows[i]}")
    subworkflow_id = input("Which sub-workflow do you want to start? ")
    return int(subworkflow_id)

# convert a excel sheet to json
def excel_to_json(file, sheet_name):
    excel_df = pd.read_excel(file, sheet_name=sheet_name)
    excel_json = json.loads(excel_df.to_json(orient="records"))
    return excel_json

# write data to excel
def write_excel(file, sheet_name, data):
    writer = pd.ExcelWriter(file, engine="openpyxl", mode="a", if_sheet_exists="replace")
    fileb = open(file, "rb")
    writer.book = openpyxl.load_workbook(fileb)
    writer.sheets = dict((ws.title, ws) for ws in writer.book.worksheets)
    df = pd.DataFrame(data)
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    writer.close()

# load mapping file
def load_mapping(workflow):
    print()
    file = input("Please provide the name of your mapping file: ")
    if workflow == 1:
        mapping = excel_to_json(file, "Commission")
    elif workflow == 3:
        mapping = excel_to_json(file, "RMA")
    elif workflow == 4:
        mapping = excel_to_json(file, "Reclassification")
    return mapping, file

# get hostname from user input
def get_hostname():
    print()
    hostname = input("Please provide the hostname of router: ")
    return hostname

# get template name from user input
def get_template_name():
    print()
    template_name = input("Please provide the template name: ")
    return template_name

# add template config via vManage SDK
def add_template_config(template_config):
    with open("import_templates.json", "w") as file:
        json.dump(template_config, file)
    os.system("vmanage import templates --file import_templates.json")

# display user menu
def menu():
    print()
    for i in range(len(workflows)):
        print(f"{i+1}. {workflows[i]}")
    workflow_id = input("Which workflow do you want to start? ")
    workflow_starter(int(workflow_id))

# define a class for vManage object
class vManage():
    def __init__(self, session):
        self.base_url = f"https://{vmanage_host}:{vmanage_port}"
        self.username = vmanage_username
        self.password = vmanage_password
        if session == None:
            self.session = requests.Session()
        else:
            self.session = session

    # login with 2 steps: get JSESSIONID and X-XSRF-TOKEN
    def authentication(self):
        # vManage authentication - get JSESSIONID
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        jsession = self.session.post(f"{self.base_url}/j_security_check", headers=headers, data=payload, verify=False)

        # vManage authentication - get X-XSRF-TOKEN
        token = self.session.get(f"{self.base_url}/dataservice/client/token")
        self.session.headers["X-XSRF-TOKEN"] = token.text

        return self.session

    # vManage get device templates
    def get_device_templates(self):
        response = self.session.get(f"{self.base_url}/dataservice/template/device", verify=False)
        response = json.loads(response.text)
        return response["data"]

    # vManage get feature templates
    def get_feature_templates(self):
        response = self.session.get(f"{self.base_url}/dataservice/template/feature", verify=False)
        response = json.loads(response.text)
        return response["data"]

    # vManage get device list
    def get_device_list(self, category="vedges"):
        response = self.session.get(f"{self.base_url}/dataservice/system/device/{category}", verify=False)
        response = json.loads(response.text)
        return response["data"]

    # vManage get template config
    def get_template_config(self, template_id):
        response = self.session.get(f"{self.base_url}/dataservice/template/device/object/{template_id}", verify=False)
        response = json.loads(response.text)
        return response

    # vManage get template input variables
    def get_template_input(self, template_id, device_id_list):
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "deviceIds": device_id_list,
            "isEdited": False,
            "isMasterEdited": False,
            "templateId": template_id
        }
        response = self.session.post(f"{self.base_url}/dataservice/template/device/config/input", headers=headers, data=json.dumps(payload), verify=False)
        response = json.loads(response.text)
        return response["data"]

    # vManage get devices attached to template
    def get_template_attached_devices(self, template_id):
        headers = {
            "Content-Type": "application/json"
        }
        response = self.session.get(f"{self.base_url}/dataservice/template/device/config/attached/{template_id}", headers=headers, verify=False)
        response = json.loads(response.text)
        return response["data"]

    # vManage add feature template
    def add_feature_template(self, template_config):
        headers = {
            "Content-Type": "application/json"
        }
        response = self.session.post(f"{self.base_url}/dataservice/template/feature", headers=headers, data=json.dumps(template_config), verify=False)
        response = json.loads(response.text)
        return response["templateId"]

    # vManage add feature template
    def add_device_template(self, template_config):
        headers = {
            "Content-Type": "application/json"
        }
        response = self.session.post(f"{self.base_url}/dataservice/template/device/feature", headers=headers, data=json.dumps(template_config), verify=False)
        response = json.loads(response.text)
        return response["templateId"]

    # vManage attach router to template
    def attach_template(self, template_id, template_input_variables):
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "deviceTemplateList": [{
                "templateId": template_id,
                "device": template_input_variables,
                "isEdited": False,
                "isMasterEdited": False
            }]
        }
        response = self.session.post(f"{self.base_url}/dataservice/template/device/config/attachfeature", headers=headers, data=json.dumps(payload), verify=False)
        response = json.loads(response.text)
        return response

    # vManage detach router from template
    def detach_template(self, device_type, device_uuid, device_ip):
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "deviceType": device_type,
            "devices": [{
                "deviceId": device_uuid,
                "deviceIP": device_ip,
            }]
        }
        response = self.session.post(f"{self.base_url}/dataservice/template/config/device/mode/cli", headers=headers, data=json.dumps(payload), verify=False)
        response = json.loads(response.text)
        return response

    # vManage invalidate router certificate
    def invalidate_certificate(self, chasis_number, serial_number):
        headers = {
            "Content-Type": "application/json"
        }
        payload = [{
            "chasisNumber": chasis_number,
            "serialNumber": serial_number,
            "validity": "invalid"
        }]
        response = self.session.post(f"{self.base_url}/dataservice/certificate/save/vedge/list", headers=headers, data=json.dumps(payload), verify=False)
        response = json.loads(response.text)
        return response

    # vManage sync controllers
    def sync_controllers(self):
        response = self.session.post(f"{self.base_url}/dataservice/certificate/vedge/list", verify=False)
        response = json.loads(response.text)
        return response

    # vManage completely remove router
    def decommission_device(self, device_uuid):
        response = self.session.put(f"{self.base_url}/dataservice/system/device/decommission/{device_uuid}", verify=False)
        response = json.loads(response.text)
        return response

    # vManage completely remove router
    def completely_remove_device(self, device_uuid):
        response = self.session.delete(f"{self.base_url}/dataservice/system/device/{device_uuid}", verify=False)
        response = json.loads(response.text)
        return response

    # vManage track action status
    def track_action_status(self, action_id):
        response = self.session.get(f"{self.base_url}/dataservice/device/action/status/{action_id}", verify=False)
        response = json.loads(response.text)
        return response["summary"]["status"]

# initialize app
if __name__ == '__main__':
    print("Initializing app...")
    menu()
