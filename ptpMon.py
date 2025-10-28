import copy
import json
from threading import Thread

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()


class ptpMon:
    def __init__(self, **kwargs):

        self.hosts = []
        self.proto = "http"

        self.parameters = []

        for key, value in kwargs.items():

            if "hosts" in key and value:
                self.hosts.extend(value)

            if "deviceType" in key and value:
                match value:
                    case 'evIPG':
                        from params.evipgParams import params, lookups
                        print(params, 'imported params')

                    case '570ipg':
                        from params.ipgParams import params, lookups
                        print(params, 'imported params')

                    case '570aco':
                        from params.acoParams import params, lookups
                        print(params, 'imported params')

                    case 'scorpion6f':
                        from params.scorpion6fParams import params, lookups
                        print(params, 'imported params')

                    case '570j2k':
                        from params.j2kParams import params, lookups
                        print(params, 'imported params')

                    case 'vip100g':
                        from params.vip100gParams import params, lookups
                        print(params, 'imported params')

                    case 'svip':
                        from params.svipParams import params, lookups
                        print(params, 'imported params')

                    case '570tg':
                        from params.tgParams import params, lookups
                        print(params, 'imported params')

                    case '570admx':
                        from params.admxParams import params, lookups
                        print(params, 'imported params')

                    case '9821aghub':
                        from params.aghubParams import params, lookups
                        print(params, 'imported params')

                self.importedParams = params
                self.importedLookups = lookups

            if "proto" in key and value:
                self.proto = value

        for template in self.importedParams:

            template_copy = copy.deepcopy(template)
            self.parameters.append(template_copy)
        

    def checkProto(self, host):
        param = [self.parameters[0]]
        print(param, 'param')
        self.proto = 'http'
        protoCheck = []

        for template in param:
            template_copy = copy.deepcopy(template)
            template_copy["id"] = template_copy["id"].format(str(0))
            protoCheck.append(template_copy)


        results = self.fetch(host, protoCheck)

        if isinstance(results, Exception):
          self.proto = 'https'
             
        else:
          self.proto = 'http'

    def fetch(self, host, parameters):

        try:

            with requests.Session() as session:

                ## get the session ID from accessing the login.php site
                resp = session.get(
                    "%s://%s/login.php" % (self.proto, host),
                    verify=False,
                    timeout=15.0,
                )

                session_id = resp.headers["Set-Cookie"].split(";")[0]

                payload = {
                    "jsonrpc": "2.0",
                    "method": "get",
                    "params": {"parameters": parameters},
                    "id": 1,
                }

                url = "%s://%s/cgi-bin/cfgjsonrpc" % (self.proto, host)

                headers = {
                    "Content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Cookie": session_id + "; webeasy-loggedin=true",
                }

                response = session.post(
                    url,
                    headers=headers,
                    data=json.dumps(payload),
                    verify=False,
                    timeout=15.0,
                )

                return json.loads(response.text)

        except Exception as error:
            return error

    def parse_results(self, host, collection):

        self.checkProto(host)
        print(self.proto)

        results = self.fetch(host, self.parameters)
        host_instance = {host: {}}
        hosts = host_instance[host]

        try:

            for result in results["result"]["parameters"]:

                # perform lookup for playout status enumeration
                if "active_ptp" in result["name"]:
                    result["value"] = self.importedLookups[0][result["value"]]

                # perform lookup for link select enumeration
                elif "ptp_status" in result["name"]:
                    result["value"] = self.importedLookups[1][result["value"]]

                if result["name"] not in hosts.keys():
                    hosts.update(
                        {
                            result["name"]: result["value"] if result["value"] != "" else 'N/A',
                            # "as_ids": [result["id"]],
                        }
                    )

                else:

                    hosts.update({result["name"]: result["value"]})
                    # hosts["as_ids"].append(result["id"])

            
            collection.update(host_instance)

        except Exception as e:
            hosts.update({
                'active_ptp': 'N/A',
                'ptp_status': 'N/A',
                's_master_identity': 'N/A',
                's_grandmaster_identity': 'N/A'
            })
            collection.update(host_instance)
            print(e)

    @property
    def collect(self):

        collection = {}

        threads = [
            Thread(
                target=self.parse_results,
                args=(
                    host,
                    collection,
                ),
            )
            for host in self.hosts
        ]

        for x in threads:
            x.start()

        for y in threads:
            y.join()
 
        return collection


#  172.17.223.117 - evipg,
#  172.17.196.238 - 570ipg10g,
#  172.17.223.61 - 570ipg25g,
#  172.17.223.105 - scorpion6f,
#  172.16.199.105 - 570j2k,
#  172.17.223.93 - vip100g,
#  172.16.199.178 - 570tg,
#  172.17.223.231 - 570emr-admx
#  172.17.223.233 - 9821aghub
#  172.16.58.89 - svip
#  172.17.238.91 - 570aco25g

def main():

    params = {"hosts": ["172.17.238.91"],  
              "deviceType": "570aco"}

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
