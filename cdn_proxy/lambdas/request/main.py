import ipaddress
import random
import re

import socket
import json
import struct

# Lambda@Edge functions cannot have environment variables, so these get replaced at deploy time.
DEFAULT_HOST = None
X_FORWARDED_FOR = None


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
    try:
        host = socket.gethostbyaddr(ip)[0]
        resolved_ip = socket.gethostbyname(host)
        if ip == resolved_ip:
            return host
        else:
            raise CDNProxyError('Unable to resolve the IP provided in Cdn-Proxy-Origin to a hostname. '
                                'Forward and reverse resolved IPs did not match. As a workaround you can specify a'
                                'hostname that resolves to this IP address.')
    except socket.herror:
        raise CDNProxyError('Unable to resolve the IP provided in Cdn-Proxy-Origin to a hostname. '
                            'Reverse ptr resolution failed. As a workaround you can specify a'
                            'hostname that resolves to this IP address.')
    except socket.gaierror:
        raise CDNProxyError('Unable to resolve the IP provided in Cdn-Proxy-Origin to a hostname. '
                            'Forward resolution of the resulting reverse ptr failed. As a workaround you can specify a'
                            'hostname that resolves to this IP address.')


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
    # Override default host if we find the Cdn-Proxy-Target header.
    if len(headers.get('cdn-proxy-origin', [])) == 1:
        value = headers['cdn-proxy-origin'][0]['value']
        origin['domainName'] = value
        if re.match(r'([0-9]{1,3}\.){3}[0-9]{1,3}', value):
            origin['domainName'] = hostname_for_ip(value)

    # Override the default origin if we get the Cdn-Proxy-Origin header.
    host = DEFAULT_HOST
    if len(headers.get('cdn-proxy-origin', [])) == 1:
        host = headers['cdn-proxy-origin'][0]['value']
    print(f'Setting Host to `{host}`.')
    if not host:
        raise UserWarning('Something went wrong, the global variable DEFAULT_HOST was not set during deploy and the '
                          'request did not have the Cdn-Proxy-Host header set.')
    headers['host'] = [{
        "key": "Host",
        "value": host,
    }]

    if X_FORWARDED_FOR:
        forwarded_for = X_FORWARDED_FOR
    else:
        forwarded_for = random_ip()
    print(f'Setting X-Forwarded-For to `{forwarded_for}`.')

    headers['x-forwarded-for'] = [{
        "key": "X-Forwarded-For",
        "value": forwarded_for,
    }]
    return headers, origin
