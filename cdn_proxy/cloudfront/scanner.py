import asyncio
from dataclasses import dataclass
from enum import Enum

import aiohttp
import aiohttp.client_exceptions

from cdn_proxy.cloudfront import CloudFront


class CloudFrontScanner(CloudFront):
    def __init__(self, *args, max: int = 20, **kwargs):
        super().__init__(*args, **kwargs)
        self._session: "aiohttp.ClientSession"
        sem = asyncio.Semaphore(20)

    async def __aenter__(self):
        conn = aiohttp.TCPConnector(verify_ssl=False)
        self._session: "aiohttp.ClientSession" = aiohttp.ClientSession(connector=conn)
        return self

    async def __aexit__(self, *err):
        await self._session.close()
        self._session: "aiohttp.ClientSession" = None  # noqa

    async def scan(self, origin: str, host: str = None):
        result = await self._scan(host, origin)

        msg = f"{str(origin)} -- Proxy: {result.ProxyState.value} / Origin: {result.OriginState.value}"
        if result.OriginState == ServiceState.Closed and (
            result.ProxyState in [ServiceState.Open, ServiceState.OpenServFail]
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
            return RequestError.Disconnected
        except (
            aiohttp.client_exceptions.ClientConnectorError,
            aiohttp.client_exceptions.ClientOSError,
        ):
            return RequestError.ClientError
        except asyncio.exceptions.TimeoutError:
            return RequestError.Timeout

    async def _check_status(self, resp):
        state = None
        if type(resp) is RequestError:
            if resp == RequestError.ClientError:
                state = ServiceState.ClientFailed
            elif resp == RequestError.Timeout:
                state = ServiceState.Filtered
            elif resp == RequestError.Disconnected:
                state = ServiceState.OpenServFail
            else:
                import pdb

                pdb.set_trace()
        elif 200 <= resp.status <= 499:
            state = ServiceState.Open
        elif resp.status == 500:
            state = ServiceState.OpenServFail
        elif resp.status in [502, 503]:
            state = ServiceState.Closed
        elif resp.status == 504:
            state = ServiceState.Filtered
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
    ClientFailed = "unknown (client failed)"
    Open = "open"
    OpenServFail = "open (server failed)"
    Closed = "closed"
    Filtered = "closed"


class RequestError(Enum):
    Disconnected = "Disconnected"
    ClientError = "ClientConnectorError"
    Timeout = "Timeout"
