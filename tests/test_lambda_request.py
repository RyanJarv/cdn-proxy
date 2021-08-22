import pytest
from cdn_proxy.lambdas.request.main import hostname_for_ip, main


def test_hostname_for_ip():
    assert hostname_for_ip('52.4.10.14') == 'ec2-52-4-10-14.compute-1.amazonaws.com'

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
  "cdn-proxy-origin": [
    {
      "key": "Cdn-Proxy-Origin",
      "value": "52.4.10.14"
    }
  ],
  "cdn-proxy-host": [
    {
      "key": "Cdn-Proxy-Host",
      "value": "52.4.10.14"
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
      "value": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
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


def test_main():
    headers_resp, origin_resp = main(headers, {
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
    })
    assert origin_resp['domainName'] == 'ec2-52-4-10-14.compute-1.amazonaws.com'