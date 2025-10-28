import json
from insite_plugin import InsitePlugin
from ptpMon import ptpMon


# Supported Device Types (use lowercase version in params):


    # 570IPG -> 570ipg
    # 570J2K -> 570j2k
    # 570ACO -> 570aco
    # 570EMR-ADMX -> 570admx
    # 9821-AG-HUB -> 9821aghub
    # evIPG-3G -> evIPG
    # SCORPION-6F -> scorpion6f
    # SCORPION-X18 -> scorpionx18
    # sVIP -> svip
    # 570TG-100G -> 570tg
    # evVIP-100G -> vip100g


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