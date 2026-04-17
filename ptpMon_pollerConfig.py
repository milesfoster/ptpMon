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
    # SCORPION-4 -> scorpion4
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
                      "eligibleRootLeaders": ["MAC-ADDRESS-1", "MAC-ADDRESS-2"],
                      "credentials": {"admin": "admin"}}

            self.collector = ptpMon(**params)

        documents = []

        host_data, perf_doc = self.collector.collect
        for host, data in host_data.items():
            if data.get("error"):
                documents.append({
                    "host": host,
                    "name": "ptpStatus",
                    "fields": {
                        "status": "error",
                        "error_message": data["error"]
                    }
                })
                continue

            else:
                document = {
                    "fields": data,
                    "host": host,
                    "name": "ptpStatus",
                    "status": "success"
                }
                documents.append(document)

        # Per-cycle performance telemetry. One doc per cycle, emitted alongside
        # the per-host ptpStatus docs so it flows through the same Poller ->
        # Elasticsearch pipeline. Visualize in Kibana to watch cycle_wall_s,
        # cycle_cpu_s, and the per-host p95/p99 latency trend over time.
        documents.append({
            "host": "ptpMon",
            "name": "ptpMonPerf",
            "fields": perf_doc,
        })

        return json.dumps(documents)