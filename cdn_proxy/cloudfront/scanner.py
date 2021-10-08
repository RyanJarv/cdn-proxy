import sys
import queue

import urllib3
import concurrent.futures
import botocore.exceptions

from dataclasses import dataclass
from enum import Enum
from typing import List, Union, cast, Dict, Optional

import requests
import requests.adapters

from requests import Session
from requests.exceptions import ConnectionError, ConnectTimeout, TooManyRedirects, Timeout

from cdn_proxy.cloudfront import CloudFront
from cdn_proxy.lib import targets_to_hosts

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _check_status(resp: Union[requests.Response, "SvcState"]) -> "SvcState":
    if type(resp) is SvcState:
        return cast(SvcState, resp)
    else:
        resp = cast(requests.Response, resp)

    if 200 <= resp.status_code <= 499:
        state = SvcState.OPEN
    elif resp.status_code == 500:
        state = SvcState.OPEN_SERV_FAIL
    elif resp.status_code in [502, 503]:
        state = SvcState.CLOSED
    elif resp.status_code == 504:
        state = SvcState.FILTERED
    else:
        state = SvcState.CLIENT_FAILED
        print("** WARNING **")
        print("  unhandled state, the following condition needs to be checked for")
        print("  type(resp): " + str(type(resp)))
        print("  resp: " + str(resp))
        print("  resp.status_code: " + str(resp.status_code))
        print("  resp.text: " + str(resp.text))

    return state


class CloudFrontScanner(CloudFront):
    def __init__(self, *args, workers: int = 20, timeout: int = 15, **kwargs):
        self.distribution = None

        try:
            super().__init__(*args, **kwargs)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ExpiredToken':
                print('[WARNING] Found expired AWS credentials.')
            else:
                raise e

        print('# of workers: ' + str(workers), flush=True)
        print('Timeout in secs: ' + str(timeout), flush=True)
        self.sem: queue.Queue = queue.Queue(maxsize=workers)
        self.timeout = timeout

        self.requests = Session()
        self.workers = workers
        adapter = requests.adapters.HTTPAdapter(pool_connections=int(workers * 2), pool_maxsize=int(workers * 2))
        self.requests.mount('http://', adapter)
        self.requests.mount('https://', adapter)

    def scan(self, targets: List[str], host: str = '', cdn_proxy: Optional[str] = None):
        try:
            origins = list(targets_to_hosts(targets))
        except ValueError as e:
            print("[ERROR] " + e.args[0])
            sys.exit(101)

        if self.distribution:
            cdn_proxy = self.distribution.domain
        elif not cdn_proxy:
            print('[ERROR] Unable to determine the CloudFront proxy domain to use.')
            sys.exit(102)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as exc:
            def _(origin: str):
                return self._scan(cast(str, cdn_proxy), origin, host)

            for r in exc.map(_, origins):
                msg = f"{r.Origin} (Host: {r.Host}) -- Proxy: {r.ProxyState.value} / Origin: {r.OriginState.value}"

                if r.OriginState == SvcState.CLOSED and (r.ProxyState in [SvcState.OPEN, SvcState.OPEN_SERV_FAIL]):
                    msg = msg + " -- Proxy Bypass Found"

                print(msg)

    def _scan(self, cdn_proxy: str, origin: str, host: str) -> "ScanResult":
        proxy_hdrs = {"Cdn-Proxy-Origin": origin}
        if host:
            proxy_hdrs["Cdn-Proxy-Host"] = host

        origin_hdrs: Dict[str, str] = {}
        if origin_hdrs:
            origin_hdrs["Host"] = host

        proxy_resp = self._fetch(cdn_proxy, proxy_hdrs)
        orig_resp = self._fetch(origin, origin_hdrs)

        result = ScanResult(
            ProxyState=_check_status(proxy_resp),
            OriginState=_check_status(orig_resp),
            Origin=origin,
            Host=host or origin,
        )
        return result

    def _fetch(self, server, hdrs=None) -> Union[requests.Response, "SvcState"]:
        if not hdrs:
            hdrs = {}
        try:
            return self.requests.get(f"https://{server}", headers=hdrs, timeout=self.timeout, verify=False)
        except TooManyRedirects:
            return SvcState.OPEN
        except (ConnectionError, ConnectTimeout, Timeout):
            return SvcState.FILTERED
        except Exception as e:
            print("** WARNING **")
            print("  unhandled exception, the following exception needs to be handled")
            print("  type(e): " + str(type(e)))
            print("  e: " + str(e))
            print("  ' '.join(e.args): " + ' '.join(e.args))
            return SvcState.CLIENT_FAILED


# TODO: Make sure https goes to https on the backend


@dataclass
class ScanResult:
    ProxyState: "SvcState"
    OriginState: "SvcState"
    Origin: str
    Host: str


class SvcState(Enum):
    CLIENT_FAILED = "unknown (client failed)"
    OPEN = "open"
    OPEN_SERV_FAIL = "open (server failed)"
    CLOSED = "closed"
    FILTERED = "closed"