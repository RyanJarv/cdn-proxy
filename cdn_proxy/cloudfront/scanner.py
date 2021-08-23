import asyncio
from dataclasses import dataclass
from enum import Enum

import aiohttp
import aiohttp.client_exceptions

from cdn_proxy.cloudfront import CloudFront


class CloudFrontScanner(CloudFront):
    def __init__(self, *args, workers: int = 20, **kwargs):
        super().__init__(*args, **kwargs)
        self._session: "aiohttp.ClientSession"
        self.sem = asyncio.Semaphore(workers)

    async def __aenter__(self):
        conn = aiohttp.TCPConnector(verify_ssl=False)
        self._session: "aiohttp.ClientSession" = aiohttp.ClientSession(connector=conn)
        return self

    async def __aexit__(self, *err):
        await self._session.close()
        self._session: "aiohttp.ClientSession" = None  # noqa

    async def scan(self, origin: str, host: str = None):
        async with self.sem:
            result = await self._scan(host, origin)

        msg = f"{str(origin)} -- Proxy: {result.ProxyState.value} / Origin: {result.OriginState.value}"
        if result.OriginState == ServiceState.CLOSED and (
            result.ProxyState in [ServiceState.OPEN, ServiceState.OPEN_SERV_FAIL]
        ):
            msg = msg + " -- Proxy Bypass Found"
        print(msg)

    async def _scan(self, host, origin) -> "ScanResult":
        proxy_hdrs = {"Cdn-Proxy-Origin": origin}
        if host:
            proxy_hdrs["Cdn-Proxy-Host"] = host

        origin_hdrs = {}
        if origin_hdrs:
            origin_hdrs["Host"] = host

        proxy_resp = await self._fetch(self.distribution.domain, proxy_hdrs)
        orig_resp = await self._fetch(origin, origin_hdrs)

        result = ScanResult(
            ProxyState=await self._check_status(proxy_resp),
            OriginState=await self._check_status(orig_resp),
        )
        return result

    async def _fetch(self, server, hdrs=None):
        if not hdrs:
            hdrs = {}
        try:
            async with self._session.get(f"https://{server}", headers=hdrs) as resp:
                proxy_resp = resp
            return proxy_resp
        except aiohttp.client_exceptions.ServerDisconnectedError:
            return RequestError.DISCONNECTED
        except (
            aiohttp.client_exceptions.ClientConnectorError,
            aiohttp.client_exceptions.ClientOSError,
        ):
            return RequestError.CLIENT_ERROR
        except asyncio.exceptions.TimeoutError:
            return RequestError.TIMEOUT

    async def _check_status(self, resp):
        state = None
        if type(resp) is RequestError:
            if resp == RequestError.CLIENT_ERROR:
                state = ServiceState.CLIENT_FAILED
            elif resp == RequestError.TIMEOUT:
                state = ServiceState.FILTERED
            elif resp == RequestError.DISCONNECTED:
                state = ServiceState.OPEN_SERV_FAIL
            else:
                import pdb

                pdb.set_trace()
        elif 200 <= resp.status <= 499:
            state = ServiceState.OPEN
        elif resp.status == 500:
            state = ServiceState.OPEN_SERV_FAIL
        elif resp.status in [502, 503]:
            state = ServiceState.CLOSED
        elif resp.status == 504:
            state = ServiceState.FILTERED
        else:
            import pdb

            pdb.set_trace()

        return state


# TODO: Make sure https goes to https on the backend


@dataclass
class ScanResult:
    ProxyState: "ServiceState"
    OriginState: "ServiceState"


class ServiceState(Enum):
    CLIENT_FAILED = "unknown (client failed)"
    OPEN = "open"
    OPEN_SERV_FAIL = "open (server failed)"
    CLOSED = "closed"
    FILTERED = "closed"


class RequestError(Enum):
    DISCONNECTED = "Disconnected"
    CLIENT_ERROR = "ClientConnectorError"
    TIMEOUT = "Timeout"
