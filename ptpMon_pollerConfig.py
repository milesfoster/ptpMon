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

# Set evaluateLeaderEligibility to True or False if you want Root Leader eligibility assessment
# If evaluateLeaderEligibility is set to true, provide eligible root leaders as they are represented on the host Webeasy
    # some represent MAC with colons, others use dashes. 00:1A:XX:XX:XX:XX vs. 00-1A-XX-XX-XX-XX

class Plugin(InsitePlugin):
    def can_group(self):
        return True

    def fetch(self, hosts):

        try:

            self.collector

        except Exception:

            params = {"hosts": hosts,
                      "deviceType": "570aco",
                      "evaluateLeaderEligibility": True,
                      "eligibleRootLeaders": ["MAC-ADDRESS-1", "MAC-ADDRESS-2"]}

            self.collector = ptpMon(**params)

        documents = []

        for host, params in self.collector.collect.items():

            document = {"fields": params, "host": host, "name": "ptpStatus"}

            documents.append(document)

        return json.dumps(documents)