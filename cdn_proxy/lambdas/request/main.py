import ipaddress
import random
import re

import socket
import json
import struct
from pathlib import Path


class CDNProxyError(Exception):
    pass


def random_ip():
    """Returns a random public IP address."""
    while True:
        ip = socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))
        _ip = ipaddress.IPv4Address(ip)
        if not any([_ip.is_private, _ip.is_reserved, _ip.is_loopback, _ip.is_multicast, _ip.is_link_local]):
            return ip


def hostname_for_ip(ip: str):
    """Returns a sslip.io hostname that resolves to the given IP address."""
    return f"{ip.replace('.', '-')}.sslip.io"


def lambda_handler(event, context):
    print('event: ' + json.dumps(event))
    request = event['Records'][0]['cf']['request']
    headers = request['headers']
    origin = request['origin']['custom']

    try:
        request['headers'], request['origin']['custom'] = main(headers, origin)
    except CDNProxyError as e:
        return {
            "body": ' '.join(e.args),
            "bodyEncoding": 'text',
            "headers": {},
            "status": '400',
            "statusDescription": 'Bad Request'
        }

    return request


def main(headers, origin):
    if len(headers.get('cdn-proxy-origin', [])) == 0:
        help_html = Path('./help.html').read_text()
        raise CDNProxyError(help_html)

    target = headers['cdn-proxy-origin'][0]['value']
    if re.match(r'([0-9]{1,3}\.){3}[0-9]{1,3}', target):
        origin['domainName'] = hostname_for_ip(target)
    else:
        origin['domainName'] = target

    # Set the origin if we get the Cdn-Proxy-Origin header. By default it is set to the value of Cdn-Proxy-Origin.
    if len(headers.get('cdn-proxy-host', [])) == 1:
        host = headers['cdn-proxy-host'][0]['value']
    else:
        host = target

    print(f'Setting Host to `{host}`.')
    headers['host'] = [{
        "key": "Host",
        "value": host,
    }]

    if len(headers.get('x-forwarded-for', [])) != 1:
        forwarded_for = random_ip()
        print(f'Setting X-Forwarded-For to `{forwarded_for}`.')
        headers['x-forwarded-for'] = [{
            "key": "X-Forwarded-For",
            "value": forwarded_for,
        }]

    return headers, origin
