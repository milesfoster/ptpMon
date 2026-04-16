import copy
import json
import statistics
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import requests
import urllib3
from requests.adapters import HTTPAdapter

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
        self.max_workers = 100

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

                    case 'scorpion4':
                        from params.scorpion4Params import params, lookups
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

            if "maxWorkers" in key and value:
                self.max_workers = int(value)


        for template in self.importedParams:

            template_copy = copy.deepcopy(template)
            self.parameters.append(template_copy)

        # Pre-serialize the JSON-RPC payload body once. self.parameters never
        # changes after __init__, so serializing per cycle (800 times per cycle)
        # was wasted CPU. fetch/auth_fetch send this verbatim.
        self.payload_body = json.dumps({
            "jsonrpc": "2.0",
            "method": "get",
            "params": {"parameters": self.parameters},
            "id": 1,
        })

        # Per-host discovery cache. Populated on first successful probe of a
        # host, reused on every subsequent cycle. Invalidated on RPC failure
        # (see parse_results) so a device that's been upgraded/downgraded
        # self-heals after one failed cycle. Relies on the Plugin instance
        # staying alive across poll cycles (user-confirmed behavior of the
        # MAGNUM-Analytics Poller).
        self.endpoint_cache = {}

        # Single shared requests.Session with a pooled HTTPAdapter. Keep-alive
        # eliminates the TLS handshake on steady-state cycles; pool sizing
        # matches max_workers so no worker blocks on an exhausted connection
        # pool. urllib3 connection pools are thread-safe.
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=max(self.max_workers, 32),
            pool_maxsize=max(self.max_workers, 32),
            max_retries=0,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.verify = False

        # Cycle-scoped telemetry containers. These are reset at the start of
        # every collect() call so each cycle's perf doc is independent.
        self._cycle_counter = Counter()
        self._cycle_timings = []
        self._cycle_lock = threading.Lock()

    def checkProto(self, host, timeout=(2, 3)):
            """
            Determines whether a host supports HTTP or HTTPS by testing HTTP first
            and following redirects. Falls back to HTTPS if HTTP fails completely.

            Uses HEAD so we don't download the login page body just to read the
            redirected URL. Uses the shared pooled session so this probe benefits
            from keep-alive when re-probing a flapping host.
            """
            test_url = f"http://{host}"
            try:
                self._cycle_counter["http_probes"] += 1
                r = self.session.head(test_url, timeout=timeout, allow_redirects=True)
                # Check if connection was upgraded
                if r.url.startswith("https://"):
                    return "https"
                else:
                    return "http"


            except requests.RequestException:
                try:
                    self._cycle_counter["http_probes"] += 1
                    r = self.session.head(f"https://{host}", timeout=timeout)
                    if r.ok:
                        return "https"

                except requests.RequestException:
                    raise ConnectionError(f"Could not connect to {host} using HTTP or HTTPS.")

    def checkEndpoint(self, host, proto):

            endpoint_url = f"{proto}://{host}/cgi-bin/"

            try:
                self._cycle_counter["http_probes"] += 1
                # GET (not HEAD) here because some servers return 405 for HEAD on
                # dynamic cgi-bin paths. Original logic depends on the 403 status.
                r = self.session.get(endpoint_url, timeout=(2, 3), allow_redirects=False)

                if r.status_code == 404:
                    n = requests.get(endpoint_url + "/cfgjsonrpc")
                    if n.status_code == 200:
                    # Direct cgi-bin acccess is blocked on older code
                        return 'cfgjsonrpc'

                    else:
                        raise requests.exception.HTTPError("cfgjsonrpc not supported: {n.status_code}")

                else:
                    # treat anything else as failure
                    raise requests.exceptions.HTTPError(f"cfgjsonrpc not supported: {r.status_code}")

            except requests.RequestException:
                # Try the auth endpoint
                try:
                    self._cycle_counter["http_probes"] += 1
                    r = self.session.head(
                        f"{proto}://{host}/v.1.5/php/datas/cfgjsonrpc.php",
                        timeout=(2, 3),
                    )

                    if r.ok:
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
            # Use the shared pooled session. The session_id cookie is read
            # straight from the Set-Cookie header and sent back via the Cookie
            # header explicitly — we don't use session.cookies, so there's no
            # cross-host cookie-jar race even with concurrent workers.
            self._cycle_counter["http_rpcs"] += 1
            resp = self.session.get(
                "%s://%s/login.php" % (proto, host),
                timeout=(3, 10),
            )

            session_id = resp.headers["Set-Cookie"].split(";")[0]

            url = "%s://%s/cgi-bin/%s" % (proto, host, endpoint)

            headers = {
                "Content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Cookie": session_id + "; webeasy-loggedin=true",
            }

            self._cycle_counter["http_rpcs"] += 1
            response = self.session.post(
                url,
                headers=headers,
                data=self.payload_body,
                timeout=(3, 10),
            )
            return json.loads(response.text)

        except Exception as error:
            return error


    def auth_fetch(self, host, proto):

        try:
            # Pass auth per-request, NOT via session.auth. session.auth is a
            # single mutable property on the shared session — setting it from
            # multiple workers concurrently would race. Per-request auth is
            # thread-safe. Credentials match the original hardcoded values.
            url = "%s://%s/v.1.5/php/datas/cfgjsonrpc.php" % (proto, host)

            headers = {"Content-type": "application/x-www-form-urlencoded; charset=UTF-8"}

            self._cycle_counter["http_rpcs"] += 1
            response = self.session.post(
                url,
                headers=headers,
                data=self.payload_body,
                auth=("root", "evertz"),
                timeout=(3, 10),
            )
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
        cache_hit = False

        try:
            # Endpoint discovery cache: if we've successfully talked to this
            # host before, skip the two discovery probes entirely. On failure
            # further down, we invalidate for next cycle (no in-cycle retry so
            # one dead host can't consume a 30s cadence budget twice).
            cached = self.endpoint_cache.get(host)
            if cached is not None:
                proto, endpoint = cached
                cache_hit = True
                self._cycle_counter["cache_hits"] += 1
            else:
                t0 = time.perf_counter()
                proto = self.checkProto(host)
                proto_ms = (time.perf_counter() - t0) * 1000.0

                t0 = time.perf_counter()
                endpoint = self.checkEndpoint(host, proto)
                endpoint_ms = (time.perf_counter() - t0) * 1000.0

                self.endpoint_cache[host] = (proto, endpoint)
                self._cycle_counter["cache_misses"] += 1

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
            # If the failure happened on a cached endpoint, the cache entry may
            # be stale (device upgraded/downgraded). Drop it so next cycle
            # re-probes. We do NOT retry in-cycle — that would double the
            # worst-case time budget for dead hosts and blow the cadence.
            if cache_hit:
                self.endpoint_cache.pop(host, None)

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

        # Capacity guardrail: if workers would each serve more than ~8 hosts
        # sequentially (per cycle), warn the operator. Raising max_workers or
        # lowering cadence is the fix.
        if self.hosts and len(self.hosts) > self.max_workers * 8:
            print(
                "ptpMon WARNING: %d hosts with max_workers=%d — consider raising "
                "max_workers via params['maxWorkers']." % (len(self.hosts), self.max_workers)
            )

        wall_start = time.perf_counter()
        cpu_start = time.process_time()
        if _HAVE_RUSAGE:
            ru_start = resource.getrusage(resource.RUSAGE_SELF)
        else:
            ru_start = None

        if self.hosts:
            # ThreadPoolExecutor replaces the old 1-thread-per-host model.
            # Bounded concurrency caps the simultaneous TLS-handshake load and
            # keeps the process's OS-thread count predictable cycle-over-cycle.
            with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                # list(...) forces iteration so exceptions inside parse_results
                # (which are caught internally anyway) don't leave lingering
                # futures; the `with` block joins all workers on exit.
                list(ex.map(lambda h: self.parse_results(h, collection), self.hosts))

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
            "endpoint_cache_hit_ratio": (
                self._cycle_counter.get("cache_hits", 0)
                / max(1, self._cycle_counter.get("cache_hits", 0)
                         + self._cycle_counter.get("cache_misses", 0))
            ),
            "endpoint_cache_size": len(self.endpoint_cache),
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
