import ipaddress
import random

import socket
import struct

# Lambda@Edge functions cannot have environment variables, so these get replaced at deploy time.
HOST = None
X_FORWARDED_FOR = None


def random_ip():
    """Returns a random public IP address."""
    while True:
        ip = socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))
        _ip = ipaddress.IPv4Address(ip)
        if not any([_ip.is_private, _ip.is_reserved, _ip.is_loopback, _ip.is_multicast, _ip.is_link_local]):
            return ip


def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request['headers']

    if not HOST:
        raise UserWarning('Something went wrong, the global variable HOST was not set during deploy.')

    if X_FORWARDED_FOR:
        forwarded_for = X_FORWARDED_FOR
    else:
        forwarded_for = random_ip()

    print(f'Setting Host to `{HOST}`.')
    headers['host'] = [{
        "key": "Host",
        "value": HOST,
    }]

    print(f'Setting X-Forwarded-For to `{forwarded_for}`.')
    headers['x-forwarded-for'] = [{
        "key": "X-Forwarded-For",
        "value": forwarded_for,
    }]

    return request
