# SD-WAN Device Lifecycle Management

An all-in-one script to manage five use cases for device lifecycle via vManage APIs: commissioning routers, decommissioning routers, replacing (RMA) routers, reclassifying routers and changing router configuration in batches.

*Commissioning routers*: This use case aims to build new routers when opening a new branch by attaching templates to the routers. Given device template names and router chassis numbers, the script exports the required template input variable fields. After providing the input values, the routers are attached to the corresponding device templates.

*Decommissioning routers*: This use case aims to tear down routers when closing an existing branch by detaching routers from templates and invalidating the routers. Given router hostnames, the routers are detached from their templates and put into invalid state. Controllers are synchronized.

*Replacing (RMA) routers*: This use case aims to replace existing routers with new routers by transferring all the configuration from the old routers to the new routers. Given a mapping of old routers and new routers, the old routers are removed from vManage or decommissioned based on a flag in mapping. The new routers then attach to the templates of the old routers and inherit all the template input values from the old routers.

*Reclassifying routers*: This use case aims to rebuild configuration on existing routers by attaching the routers to other templates. Given router chassis numbers and device template names, the script exports the required template input variable fields. After providing the input values, the routers are attached to the corresponding device templates.

*Changing router configuration in batches*: This use case aims to change router configuration in the same template in batches. This avoids a change on template leading to immediate impact to all the attached routers. Given the device template name, the script creates a copy of the template, changes the new template configuration (hard coded in this script, adding a feature template of SVI Vlan100), and moves the attached routers to the new template in batches at a specified interval.



## Contacts
* Alvin Lau (alvlau@cisco.com)
* Al da Silva (aldasil@cisco.com)
* Nick Morison (nmorison@cisco.com)
* Swati Singh (swsingh3@cisco.com)



## Solution Components
* SD-WAN
* Python 3.7



## Prerequisite
- **SD-WAN**
  1. Routers should be onboarded on vManage. This script does not handle automation from Plug-and-Play (PnP) Portal.
  2. Device templates and feature templates should be created and configured as per required configuration.

- **Mapping File** - an excel file containing the input for use cases in different spreadsheets ([sample](./sandbox.xlsx))
  1. Commissioning routers
    - Spreadsheet name: Commission
    - Description: This spreadsheet maps the template assignment to the routers that are not attached to any template, grouped by a template in each row. It is a 1-to-many mapping per row. Under "TemplateName", put one template name per row. For "DeviceChassisNumber", put all the routers (chassis numbers) that should be attached to the template specified in the same row. Chassis numbers should be separated by a comma (,).
  2. Replacing (RMA) routers
    - Spreadsheet name: RMA
    - Description: This spreadsheet maps the chassis numbers of old routers and new routers. It is a 1-to-1 mapping per row. Put "Y" under "RMAviaTAC" if you want to completely remove the old router from vManage for reasons like official RMA to Cisco TAC. Otherwise, put "N" under "RMAviaTAC" to decommission the old router and put it into invalid state.
  3. Reclassifying routers
    - Spreadsheet name: Reclassification
    - Description: This spreadsheet maps the new template assignment to the routers that are currently attached to another template. It is a 1-to-1 mapping per row. Under "DeviceChassisNumber", put one router chassis number per row. For "TemplateName", put the name of a template that should be for the router specified in the same row.

- **Python 3.7** - [Installation](https://www.python.org/downloads/)



## Installation

1. Please feel free to use your SD-WAN environment if you have one available. Otherwise, we will use DevNet Sandbox as our SD-WAN environment. Please go to Cisco DevNet and reserve the sandbox [Cisco SD-WAN 19.2](https://devnetsandbox.cisco.com/RM/Diagram/Index/c9679e49-6751-4f43-9bb4-9d7ee162b069?diagramType=Topology). It takes around 10 minutes to prepare the sandbox. You may continue with the steps below.

2. To set up the script in your local workstation, download this repository, or clone this repository by `git clone <this_repo>`.

2. Optionally, create a Python 3 virtual environment.
```
python3 -m venv venv
source venv/bin/activate
```

3. Install the dependencies. Run `pip install -r requirement.txt`

4. Update environment variables in .env file.

5. Run the script by `python bot.py` when the sandbox is ready.

6. Follow along the menus and input the required information. When prompt to input mapping file name, you can put "sandbox.xlsx" as this file comes with the repository as a sample to work with the DevNet sandbox environment. For steps to provide template input values, you should fill in the new spreadsheets (named by template names) created by the script in the excel file.



## License
Provided under Cisco Sample Code License, for details see [LICENSE](./LICENSE)



## Code of Conduct
Our code of conduct is available [here](./CODE_OF_CONDUCT.md)



## Contributing
See our contributing guidelines [here](./CONTRIBUTING.md)
