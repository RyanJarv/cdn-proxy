import os
import re
from copy import copy
from pathlib import Path

import pytest
from cdn_proxy.lambdas.request.main import hostname_for_ip, main, random_ip, CDNProxyError

headers = {
    "host": [
        {
          "key": "Host",
          "value": "dldsnpcikv3j3.cloudfront.net"
        }
    ],
    "accept-language": [
        {
          "key": "Accept-Language",
          "value": "en-US,en;q=0.9"
        }
    ],
    "accept": [
        {
          "key": "Accept",
          "value": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
        }
    ],
    "cloudfront-forwarded-proto": [
        {
          "key": "CloudFront-Forwarded-Proto",
          "value": "http"
        }
    ],
    "x-forwarded-for": [
        {
          "key": "X-Forwarded-For",
          "value": "76.121.136.156"
        }
    ],
    "user-agent": [
        {
          "key": "User-Agent",
          "value": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/92.0.4515.159 Safari/537.36"
        }
    ],
    "via": [
        {
          "key": "Via",
          "value": "1.1 51225f5c5330265d7843e199c081f2d9.cloudfront.net (CloudFront)"
        }
    ],
    "cache-control": [
        {
          "key": "Cache-Control",
          "value": "max-age=0"
        }
    ],
    "upgrade-insecure-requests": [
        {
          "key": "Upgrade-Insecure-Requests",
          "value": "1"
        }
    ],
    "accept-encoding": [
        {
          "key": "Accept-Encoding",
          "value": "gzip, deflate"
        }
    ],
    "if-none-match": [
        {
          "key": "If-None-Match",
          "value": "\"3147526947\""
        }
    ],
    "if-modified-since": [
        {
          "key": "If-Modified-Since",
          "value": "Thu, 17 Oct 2019 07:18:26 GMT"
        }
    ]
}

origin = {
    "custom": {
        "customHeaders": {},
        "domainName": "example.com",
        "keepaliveTimeout": 5,
        "path": "",
        "port": 80,
        "protocol": "http",
        "readTimeout": 30,
        "sslProtocols": [
            "TLSv1",
            "TLSv1.1",
            "TLSv1.2",
            "SSLv3"
        ]
    }
}


def test_hostname_for_ip():
    assert hostname_for_ip('52.4.10.14') == '52-4-10-14.sslip.io'


def test_random_ip():
    ip1 = random_ip()
    assert re.match(r'([0-9]{1,3}\.){3}[0-9]{1,3}', ip1)
    ip2 = random_ip()
    assert re.match(r'([0-9]{1,3}\.){3}[0-9]{1,3}', ip2)
    assert ip1 != ip2


def test_main():
    _headers = copy(headers)
    _headers["cdn-proxy-origin"] = [
        {
            "key": "Cdn-Proxy-Origin",
            "value": "52.4.10.14"
        }
    ]
    _headers["cdn-proxy-host"] = [
        {
            "key": "Cdn-Proxy-Host",
            "value": "test-host"
        }
    ]
    headers_resp, origin_resp = main(_headers, origin)
    assert origin_resp['domainName'] == '52-4-10-14.sslip.io'
    assert len(headers_resp['host']) == 1
    assert headers_resp['host'][0]['value'] == 'test-host'


def test_help():
    _headers = copy(headers)
    with pytest.raises(CDNProxyError):
        os.chdir(Path(__file__).parents[1]/'cdn_proxy/lambdas/request')
        main(_headers, origin)