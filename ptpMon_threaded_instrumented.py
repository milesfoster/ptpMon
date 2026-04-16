import copy
import json
import statistics
import threading
import time
from collections import Counter
from threading import Thread

import requests
import urllib3

try:
    import resource  # POSIX only; absent on Windows dev boxes
    _HAVE_RUSAGE = True
except ImportError:
    _HAVE_RUSAGE = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()


def _quantile(values, q):
    """Return the q-th percentile (q in 0..100) of values, or 0 if empty.

    Uses statistics.quantiles with n=100; falls back to max for high q on small
    samples where quantiles would otherwise raise.
    """
    if not values:
        return 0
    if len(values) == 1:
        return values[0]
    try:
        cuts = statistics.quantiles(values, n=100, method="inclusive")
        # cuts has 99 entries: the q-th percentile is cuts[q-1] for q in 1..99
        idx = max(1, min(99, int(q))) - 1
        return cuts[idx]
    except statistics.StatisticsError:
        return max(values)


class ptpMon:
    def __init__(self, **kwargs):

        self.hosts = []
        self.proto = ""
        self.auth = None
        self.credentials = None

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

                    case 'scorpionx18':
                        from params.scorpionx18Params import params, lookups
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

            if "evaluateLeaderEligibility" in key and value:
                self.evalEligibility = value

            if "eligibleRootLeaders" in key and value:
                self.eligibleLeaders = value

            if "proto" in key and value:
                self.proto = value
            
            if "credentials" in key and value:
                self.auth = True
                self.credentials = value


        for template in self.importedParams:

            template_copy = copy.deepcopy(template)
            self.parameters.append(template_copy)

        # Cycle-scoped telemetry containers. These are reset at the start of
        # every collect() call so each cycle's perf doc is independent.
        self._cycle_counter = Counter()
        self._cycle_timings = []
        self._cycle_lock = threading.Lock()

    def checkProto(self, host, timeout=3):
            """
            Determines whether a host supports HTTP or HTTPS by testing HTTP first
            and following redirects. Falls back to HTTPS if HTTP fails completely.
            """
            test_url = f"http://{host}"
            print(test_url)
            try:
                self._cycle_counter["http_probes"] += 1
                r = requests.get(test_url, timeout=timeout, verify=False, allow_redirects=True)
                # Check if connection was upgraded
                if r.url.startswith("https://"):
                    return "https"
                else:
                    return "http"


            except requests.RequestException:
                try:
                    self._cycle_counter["http_probes"] += 1
                    r = requests.head(f"https://{host}", verify=False, timeout=timeout)
                    if r.ok:
                        return "https"

                except requests.RequestException:
                    raise ConnectionError(f"Could not connect to {host} using HTTP or HTTPS.")

    def checkEndpoint(self, host, proto):

            endpoint_url = f"{proto}://{host}/cgi-bin/"

            try:
                self._cycle_counter["http_probes"] += 1
                r = requests.get(endpoint_url, verify=False, timeout=5)

                if r.status_code == 403:
                    # Direct cgi-bin acccess is blocked on older code
                    return 'cfgjsonrpc'

                else:
                    # treat anything else as failure
                    raise requests.exceptions.HTTPError(f"cfgjsonrpc not supported: {r.status_code}")

            except requests.RequestException:
                # Try the auth endpoint
                try:
                    self._cycle_counter["http_probes"] += 1
                    r = requests.head(
                        f"{proto}://{host}/v.1.5/php/datas/cfgjsonrpc.php",
                        verify=False,
                        timeout=5
                    )

                    if r.ok:
                        print('Using delegate')
                        return "/v.1.5/php/datas/cfgjsonrpc.php"

                    else:
                        raise ConnectionError(
                            f"Bad status for v.1.5 endpoint: {r.status_code}"
                        )

                except requests.RequestException:
                    raise ConnectionError(
                        f"Could not find valid endpoint on {host}(cfgjsonrpc or delegate)."
                    )

    def fetch(self, host, proto, endpoint):

        try:

            with requests.Session() as session:

                ## get the session ID from accessing the login.php site
                self._cycle_counter["http_rpcs"] += 1
                resp = session.get(
                    "%s://%s/login.php" % (proto, host),
                    verify=False,
                    timeout=15.0,
                )

                session_id = resp.headers["Set-Cookie"].split(";")[0]

                payload = {
                    "jsonrpc": "2.0",
                    "method": "get",
                    "params": {"parameters": self.parameters},
                    "id": 1,
                }

                url = "%s://%s/cgi-bin/%s" % (proto, host, endpoint)
                print(url)

                headers = {
                    "Content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Cookie": session_id + "; webeasy-loggedin=true",
                }

                self._cycle_counter["http_rpcs"] += 1
                response = session.post(
                    url,
                    headers=headers,
                    data=json.dumps(payload),
                    verify=False,
                    timeout=15.0,
                )
                print(response.status_code)
                return json.loads(response.text)

        except Exception as error:
            return error


    def auth_fetch(self, host, proto):

        try:

            with requests.Session() as session:

                session.auth = ("root", "evertz")

                payload = {
                    "jsonrpc": "2.0",
                    "method": "get",
                    "params": {"parameters": self.parameters},
                    "id": 1,
                }

                url = "%s://%s/v.1.5/php/datas/cfgjsonrpc.php" % (proto, host)

                headers = {"Content-type": "application/x-www-form-urlencoded; charset=UTF-8"}

                self._cycle_counter["http_rpcs"] += 1
                response = session.post(
                    url,
                    headers=headers,
                    data=json.dumps(payload),
                    verify=False,
                    timeout=15.0,
                )
                print(response.status_code)
                return json.loads(response.text)

        except Exception as error:
            return error
            
    def parse_results(self, host, collection):

        host_instance = {host: {}}
        hosts = host_instance[host]

        # Per-host timing. Recorded regardless of success/failure so the perf
        # doc reflects the real distribution including slow failures.
        host_start = time.perf_counter()
        proto_ms = endpoint_ms = rpc_ms = parse_ms = 0.0

        try:
            t0 = time.perf_counter()
            proto = self.checkProto(host)
            proto_ms = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            endpoint = self.checkEndpoint(host, proto)
            endpoint_ms = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            if endpoint == '/v.1.5/php/datas/cfgjsonrpc.php':
                results = self.auth_fetch(host, proto)

            else:
                results = self.fetch(host, proto, endpoint)
            rpc_ms = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            for result in results["result"]["parameters"]:

                # perform lookup for playout status enumeration
                if "active_ptp" in result["name"]:
                    result["value"] = self.importedLookups[0][result["value"]]

                # perform lookup for link select enumeration
                elif "ptp_status" in result["name"]:
                    result["value"] = self.importedLookups[1][result["value"]]

                # evaluate if root leader is part of the provided eligible list
                if self.evalEligibility:
                    if "grandmaster_identity" in result["name"]:
                        hosts.update(
                            {
                                "b_followingEligibleRootLeader": "True" if result["value"] in self.eligibleLeaders else "False"
                            }
                        )

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

            if hosts.get("ptp_status") != "Converged":
                hosts.update({"b_followingEligibleRootLeader": "False"})

            parse_ms = (time.perf_counter() - t0) * 1000.0
            collection.update(host_instance)

        except Exception as e:
            hosts["error"] = str(e)
            collection.update(host_instance)
            self._cycle_counter["errors"] += 1

        finally:
            total_ms = (time.perf_counter() - host_start) * 1000.0
            timing = {
                "host": host,
                "proto_ms": proto_ms,
                "endpoint_ms": endpoint_ms,
                "rpc_ms": rpc_ms,
                "parse_ms": parse_ms,
                "total_ms": total_ms,
            }
            with self._cycle_lock:
                self._cycle_timings.append(timing)

    @property
    def collect(self):
        """Run one poll cycle across all hosts and return (host_data, perf_doc).

        host_data: {hostname: {field: value, ...}, ...}  (unchanged from before)
        perf_doc:  {"host_count": ..., "cycle_wall_s": ..., ...}  (new, Phase 0)

        The Plugin.fetch wrapper unpacks this tuple and emits the perf doc as a
        separate ptpMonPerf document alongside the ptpStatus documents.
        """

        # Reset cycle-scoped telemetry containers.
        self._cycle_counter = Counter()
        self._cycle_timings = []

        collection = {}

        wall_start = time.perf_counter()
        cpu_start = time.process_time()
        if _HAVE_RUSAGE:
            ru_start = resource.getrusage(resource.RUSAGE_SELF)
        else:
            ru_start = None

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

        cycle_wall_s = time.perf_counter() - wall_start
        cycle_cpu_s = time.process_time() - cpu_start

        # Snapshot per-host timings under lock so we can safely read without
        # racing against any late-finishing threads (all joined above, but be
        # defensive in case parse_results is ever refactored).
        with self._cycle_lock:
            timings = list(self._cycle_timings)

        totals = [t["total_ms"] for t in timings]
        rpcs = [t["rpc_ms"] for t in timings]
        protos = [t["proto_ms"] for t in timings]
        endpoints = [t["endpoint_ms"] for t in timings]

        perf_doc = {
            "host_count": len(self.hosts),
            "cycle_wall_s": round(cycle_wall_s, 4),
            "cycle_cpu_s": round(cycle_cpu_s, 4),
            "http_probes": self._cycle_counter.get("http_probes", 0),
            "http_rpcs": self._cycle_counter.get("http_rpcs", 0),
            "errors": self._cycle_counter.get("errors", 0),
            "active_threads": threading.active_count(),
            "per_host_total_ms_p50": round(_quantile(totals, 50), 2),
            "per_host_total_ms_p95": round(_quantile(totals, 95), 2),
            "per_host_total_ms_p99": round(_quantile(totals, 99), 2),
            "per_host_total_ms_max": round(max(totals), 2) if totals else 0,
            "per_host_rpc_ms_p95": round(_quantile(rpcs, 95), 2),
            "per_host_proto_ms_p95": round(_quantile(protos, 95), 2),
            "per_host_endpoint_ms_p95": round(_quantile(endpoints, 95), 2),
            # endpoint_cache_hit_ratio is Phase 1 territory; emitted as 0.0
            # here so the Kibana field mapping is consistent across A/B.
            "endpoint_cache_hit_ratio": 0.0,
        }

        if _HAVE_RUSAGE and ru_start is not None:
            ru_end = resource.getrusage(resource.RUSAGE_SELF)
            perf_doc.update({
                "cycle_user_s": round(ru_end.ru_utime - ru_start.ru_utime, 4),
                "cycle_sys_s": round(ru_end.ru_stime - ru_start.ru_stime, 4),
                # ru_maxrss is peak-RSS-since-process-start, not per-cycle. We
                # still emit it so sustained memory growth is visible.
                "peak_rss_kb": ru_end.ru_maxrss,
                "voluntary_ctx_switches": ru_end.ru_nvcsw - ru_start.ru_nvcsw,
                "involuntary_ctx_switches": ru_end.ru_nivcsw - ru_start.ru_nivcsw,
            })

        return collection, perf_doc


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

    params = {"hosts": ["172.17.223.117", "172.17.223.214"],  
              "deviceType": "evIPG",
              "evaluateLeaderEligibility": True,
              "eligibleRootLeaders": ["MAC-1", "00-02-C5-FF-FE-21-62-0A"],
               # Optional, but some devices enforce basic auth
              "credentials" : {"root" : "evertz"}}

    collector = ptpMon(**params)

    inputQuit = False

    while inputQuit != "q":
        documents = []

        host_data, perf_doc = collector.collect
        for host, data in host_data.items():
            # Handle host-level errors
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

            # Handle successful data
            else:
                document = {
                    "fields": data,
                    "host": host,
                    "name": "ptpStatus",
                    "status": "success"
                }
                documents.append(document)

        documents.append({
            "name": "ptpMonPerf",
            "fields": perf_doc,
        })

        print(json.dumps(documents, indent=1))
        inputQuit = input("\nType q to quit or just hit enter: ")


if __name__ == "__main__":
    main()
