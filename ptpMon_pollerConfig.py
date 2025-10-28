import json
from insite_plugin import InsitePlugin
from ptpMon import ptpMon


class Plugin(InsitePlugin):
    def can_group(self):
        return True

    def fetch(self, hosts):

        try:

            self.collector

        except Exception:

            params = {"hosts": hosts,
                      "deviceType": "570aco"}

            self.collector = ptpMon(**params)

        documents = []

        for host, params in collector.collect.items():

            document = {"fields": params, "host": host, "name": "ptpStatus"}

            documents.append(document)

        return json.dumps(documents)