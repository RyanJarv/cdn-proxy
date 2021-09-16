import ipaddress
import random
import re

import socket
import json
import struct
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs


class CDNProxyError(Exception):
    pass


def random_ip():
    """Returns a random public IP address."""
    while True:
        ip = socket.inet_ntoa(struct.pack(">I", random.randint(1, 0xFFFFFFFF)))
        _ip = ipaddress.IPv4Address(ip)
        if not any(
                [
                    _ip.is_private,
                    _ip.is_reserved,
                    _ip.is_loopback,
                    _ip.is_multicast,
                    _ip.is_link_local,
                ]
        ):
            return ip


def hostname_for_ip(ip: str):
    """Returns a sslip.io hostname that resolves to the given IP address."""
    return f"{ip.replace('.', '-')}.sslip.io"


def lambda_handler(event, context):
    print("event: " + json.dumps(event))
    request = event["Records"][0]["cf"]["request"]

    try:
        main(request)
    except CDNProxyError as e:
        return {
            "body": " ".join(e.args),
            "bodyEncoding": "text",
            "headers": {},
            "status": "400",
            "statusDescription": "Bad Request",
        }

    return request


def main(request):
    hdrs = request['headers']
    qs = request['querystring']
    backend = get_backend_from_req(hdrs, qs)
    if backend:
        request["origin"]["custom"]["domainName"] = backend
    else:
        index_html = Path("./index.html").read_text()
        raise CDNProxyError(index_html)
    request["origin"]["custom"]['domainName'] = backend

    host = get_host_from_req(hdrs, qs)
    if not host:
        host = backend
    request['headers']['host'] = [
        {
            "key": "Host",
            "value": host,
        }
    ]
    if len(request['headers'].get("x-forwarded-for", [])) != 1:
        forwarded_for = random_ip()
        print(f"Setting X-Forwarded-For to `{forwarded_for}`.")
        request['headers']['x-forwarded-for'] = [
            {
                "key": "X-Forwarded-For",
                "value": forwarded_for,
            }
        ]


def get_backend_from_req(headers, querystring) -> Optional[str]:
    origin_hdrs = headers.get("cdn-proxy-origin", [])
    origin_params = parse_qs(querystring).get("cdn-proxy-origin", [])

    if len(origin_hdrs) >= 1:
        backend = origin_hdrs[0]["value"]
    elif len(origin_params) >= 1:
        backend = origin_params[0]
    else:
        return None

    if re.match(r"([0-9]{1,3}\.){3}[0-9]{1,3}", backend):
        backend = hostname_for_ip(backend)

    return backend


def get_host_from_req(headers, querystring):
    host_hdrs = headers.get("cdn-proxy-host", [])
    host_params = parse_qs(querystring).get("cdn-proxy-host", [])

    if len(host_hdrs) == 1:
        host = host_hdrs[0]["value"]
    elif len(host_params) >= 1:
        host = host_params[0]
    else:
        host = False
    return host


