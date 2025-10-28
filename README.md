## PTP Mon

ptpMon is designed for the MAGNUM-Analytics Poller application. This poller uses the cfgjsonrpc webeasy program to retrieve device PTP state. 

The following devices are currently supported with the following arg names:

  - 570IPG -> 570ipg
  - 570J2K -> 570j2k
  - 570ACO -> 570aco
  - 570EMR-ADMX -> 570admx
  - 9821-AG-HUB -> 9821aghub
  - evIPG-3G -> evIPG
  - SCORPION-6F -> scorpion6f
  - SCORPION-X18 -> scorpionx18
  - sVIP -> svip
  - 570TG-100G -> 570tg
  - evVIP-100G -> vip100g

### Prerequisites

- Magnum-ANALYTICS Version 11 or newer
- Python 3.5.2 or newer (already installed on Analytics HW)
- Python3 Requests Library (already installed on Analytics HW)

### Installation


1. Copy ptpMon.py script to the /pll-1/data/python/modules directory via WinSCP or Command Line:
    ```sh
    cp ptpMon.py /opt/evertz/insite/parasite/applications/pll-1/data/python/modules
    ```

2. Copy the params folder to the same location as Step 1.

3. Restart the poller application
   ```sh
   git clone https://github.com/github_username/repo_name.git
   ```


### Configuration
**NOTE: Configure one poller per device type.**

1. Once the module has been installed to the correct directory, navigate to the Poller application
2. Click the "+" icon at the top right> Custom Poller to open the poller creation menu
3. Enter a Name, Summary, and any relevant Description info
4. Enter the list of hosts to poll in the Hosts tab
5. In the Input tab, change the type to Python
6. In the Input tab, change the Metric Set Name field to "ptpmetrics"
7. From the Python tab, select the Advanced tab and enable the CPython Bindings option
8. Select the Script tab and paste the contents of poller_config.py into the panel.
9. Ensure the deviceType parameter matches one of the available deviceTypes defined in the poller config file.
10. Save changes, then restart the poller program


## Testing

The ptpMon.py script can be run manually from the terminal using the following command:

```sh
sudo python3 ptpMon.py
```

However, please note that the main function params will have to be modified. At the bottom you can modify the main block:

```
def main():

    params = {"hosts": ["yourDeviceIPhere"],  
              "deviceType": "yourDeviceTypeHere"}

    collector = ptpMon(**params)

    inputQuit = False

    while inputQuit is not "q":

        documents = []

        for host, params in collector.collect.items():

            document = {"fields": params, "host": host, "name": "ptpStatus"}

            documents.append(document)

        print(json.dumps(documents, indent=1))

        inputQuit = input("\nType q to quit or just hit enter: ")


if __name__ == "__main__":
    main()
```

```

## Roadmap

- [ ] Include Kibana Objects for import
- [ ] Add additional device types
