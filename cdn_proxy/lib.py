import ipaddress
from typing import List, Generator


class CdnProxyException(Exception):
    pass


def trim(s: str, length: int):
    if len(s) <= length:
        return s
    else:
        return s[0:length] + '...'


def networks_to_hosts(networks: List[str]) -> Generator[str, None, None]:
    for net in networks:
        for host in ipaddress.ip_network(net).hosts():
            yield host
