import ipaddress
import re
from pathlib import Path
from threading import Thread
from typing import List, Generator, Callable


class CdnProxyException(Exception):
    pass


def trim(s: str, length: int):
    if len(s) <= length:
        return s
    else:
        return s[0:length] + "..."


def targets_to_hosts(networks: List[str]) -> Generator[str, None, None]:
    for net in networks:
        p = Path(net)
        if p.is_file():
            for m in re.finditer(r'([0-9]{1,3}\.){3}[0-9]{1,3}(?:/\d\d?)?', p.read_text()):
                for host in ipaddress.ip_network(m.group(0)).hosts():
                    yield str(host)
        else:
            for host in ipaddress.ip_network(net).hosts():
                yield str(host)