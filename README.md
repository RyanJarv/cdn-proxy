# CDN Proxy
[![Tests](https://github.com/RhinoSecurityLabs/cdn-proxy/actions/workflows/tests.yml/badge.svg)](https://github.com/RhinoSecurityLabs/cdn-proxy/actions/workflows/tests.yml)

A tool that can be used by web app pentesters to create a copy of the targeted website with CDN and WAF restrictions
disabled.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [CloudFront](#cloudfront)
  - [CloudFlare](#cloudflare)
- [Burp Suite Extension](#burp-suite-extension)
- [Support](#support)
- [Contributing](#contributing)


## Overview

cdn-proxy is a set of tools for bypassing IP allow listing intended to restrict origin access to requests originating
from shared CDNs.

Bypassing protections at the CDN layer through direct access is well documented, however a common response to prevent
the issue is to set up IP allow listing from the CDNs shared network range. Because shared CDNs use a common pool of
IPs for origin requests these IP restrictions can be bypassed by routing traffic through a second attacker controlled
distribution on the same network.

When configuration of this second (proxy) distribution is controlled by the attacker requests are not subject to the
same security requirements as the intended distribution. WAFs, ratelimiting, filtering, and any authentication
implemented in the intended distribution will not apply for requests passing through the proxy distribution.

Requests passing through the distribution may also be controlled by the attacker to some extend, however this depends
largely on configuration options available. In the case of CloudFront some parts of the request as well as the intended
origin can be controlled by code in a Lambda@Edge function, this allows for controlling the X-Forwarded-For header
potentially allowing for IPs to be spoofed in the backend web app as well as quickly scanning a large number of origins
to determine if they are susceptible to this attack.

![CDN Proxy Diagram](./docs/cdn-proxy-diagram.png)

https://user-images.githubusercontent.com/4079939/130310987-3ad7e7b4-db7f-4a6e-b511-14ef7a9dbab4.mov

## Prerequisites

* CloudFlare or CloudFront is used to filter or restrict traffic.
  * This likely applies to other CDNs as well, this is just what is supported currently.
* You know the origin IP (the one behind the CDN).
* IP whitelisting is used to restrict access to the origin.
  * If you can access the origin directly this tool isn't needed.

Additionally, in the case of CloudFlare, the origin web app uses a default virtual host to serve the website, or you
have access to an enterprise CloudFlare account.

## Installation

Currently, you can use pip to install directly from this repo.

```sh
python3 -m venv venv
pip3 install git+ssh://git@github.com/RhinoSecurityLabs/cdn-proxy.git
cdn-proxy --help
```

## Usage

The structure for cdn-proxy commands is `cdn-proxy [provider] [action] ...` where:

Provider is:
* `cloudfront`
* `cloudflare`
  
Action is:
* `create <target>`
* `delete <target>` 
* `list` 

The process and required options is different between providers, refer to the provider sections below for more details.

### CloudFront

#### Overview

The CloudFront module will set up the distribution that acts as a proxy through CloudFront. The origin and host header
can be controlled per request by setting the Cdn-Proxy-Origin and Cdn-Proxy-Host headers. The X-Forwarded-For header
will also be passed through from the client, if this isn't set howeveer it will default to a random IP address in the
request to the origin which will allow bypassing app side IP ratelimiting in some cases.

After deploying navigating to the distribution will show a help page with more info on headers to control the request
as well as some examples.

In addition to making requests manually with curl you can use the CDN Proxy's [Burp Suite Extension](#burp-suite-extension)
to proxy all Burp requests through the CloudFront proxy. Among other things this allows you to browse any sites only
exposed to CloudFront IPs like you normally would through the built in Burp browser.

Since it's possible to dynamically set the backend per request with the CloudFront deployment we can iterate through
a list of IP's comparing HTTP responses (or lack of) directly vs through the proxy fairly quickly. If we can't reach the IP
directly but can through the proxy then we know IP allowlisting to the CloudFront network is in effect.

Below is the output of scanning origins through CloudFront.


```
% cdn-proxy cloudfront scan ./ips.txt
# of workers: 20
Timeout in secs: 15
1.1.1.1 (Host: 1.1.1.1) -- Proxy: open / Origin: open
1.1.1.2 (Host: 1.1.1.2) -- Proxy: open / Origin: open
1.1.1.3 (Host: 1.1.1.3) -- Proxy: open / Origin: open
1.1.1.4 (Host: 1.1.1.4) -- Proxy: closed / Origin: closed
1.1.1.5 (Host: 1.1.1.5) -- Proxy: closed / Origin: closed
1.1.1.6 (Host: 1.1.1.6) -- Proxy: closed / Origin: closed
1.1.1.7 (Host: 1.1.1.7) -- Proxy: closed / Origin: closed
1.1.1.8 (Host: 1.1.1.8) -- Proxy: closed / Origin: closed
1.1.1.9 (Host: 1.1.1.9) -- Proxy: closed / Origin: closed
1.1.1.10 (Host: 1.1.1.10) -- Proxy: closed / Origin: closed
```

If the scan subcommand finds a valid file path as one of the arguments, cdn-proxy will search the file for IPs
or CIDRs and scan each one found. This means you can simply point it to any text file that may contain configuration
data, for example a terraform config file, it will pull out the valid IPs and CIDRs from it for scanning.

Otherwise, if the argument is not a valid file, it should be file or CIDR to be scanned. Multiple arguments can be
passed, as well as types mixed, so IPs, CIDRs, and file paths can all be specified in the same command.


#### Caveats

For the CloudFront module the target must be a hostname, this is a restriction in CloudFront on origin values of a
distribution. To work around this, you might want to check to see if a given IP resolves to a usable hostname through
a reverse IP DNS lookup. Worst case you can also set up your own public DNS record that resolves to the IP you want
to target.

The CloudFront module also is fairly slow and may take a while to set up and tear down.

#### Usage

```
Usage: cdn_proxy cloudfront [OPTIONS] COMMAND [ARGS]...

  Manage CloudFront distributions

Options:
  --region REGION    Sets the AWS region.  [default: us-east-1]
  --profile PROFILE  Shared credential profile to use.
  --help             Show this message and exit.

Commands:
  create  Create a new CloudFront distribution and Lambda@Edge function...
  delete  Disable and delete the specified distribution.
  list    List CloudFront distributions IDs and targets created with...
  scan    HTTP scan of IP's both directly and via proxy...
```


```
Usage: cdn_proxy cloudfront scan [OPTIONS] [TARGETS]...

  HTTP scan of targets both directly and through the deployed proxy distribution.

Arguments:
  TARGETS...  List of IPs, CIDRs, or file paths (containing IPs or CIDRs)

Options:
  --workers INTEGER  Max concurrent workers.  [default: 20]
  --timeout INTEGER  Request timeout in seconds.  [default: 15]
  --host TEXT        String to set the host headert to, defaults to the origin being scanned.
  --cdn-proxy TEXT   CDN Proxy domain name, if it can not be determened automatically.
  -h, --help         Show this message and exit.
```

### CloudFlare

#### Overview

The CloudFlare module requires an existing zone to exist in the account already. It however is much faster to add/remove
proxies then the CloudFront module.

#### Caveats

One shortcoming of this module is that it does not set the host header to the target domain after the request passes
through the CDN. This means this module will only be effective on origins that have a default virtual host set up
hosting the website you're targeting.

You can work around this limitation if you have an enterprise CloudFlare account. This is not handled by cdn-proxy
currently, however you can configure this manually using a transform rule in your zone configuration. If you want to
see support for this added to cdn-proxy let us know in a GitHub issue.

#### Scan

Since it's possible to dynamically set the backend per request with the CloudFront deployment we can iterate through
a list of IP's comparing HTTP responses (or lack of) directly vs through the proxy. If we can't reach the IP directly
but can through the proxy then we know IP allowlisting to the CloudFront network is in effect.

```
% cdn-proxy cloudfront scan ./ips.txt
# of workers: 20
Timeout in secs: 15
1.1.1.1 (Host: 1.1.1.1) -- Proxy: open / Origin: open
1.1.1.2 (Host: 1.1.1.2) -- Proxy: open / Origin: open
1.1.1.3 (Host: 1.1.1.3) -- Proxy: open / Origin: open
1.1.1.4 (Host: 1.1.1.4) -- Proxy: closed / Origin: closed
1.1.1.5 (Host: 1.1.1.5) -- Proxy: closed / Origin: closed
1.1.1.6 (Host: 1.1.1.6) -- Proxy: closed / Origin: closed
1.1.1.7 (Host: 1.1.1.7) -- Proxy: closed / Origin: closed
1.1.1.8 (Host: 1.1.1.8) -- Proxy: closed / Origin: closed
1.1.1.9 (Host: 1.1.1.9) -- Proxy: closed / Origin: closed
1.1.1.10 (Host: 1.1.1.10) -- Proxy: closed / Origin: closed
```

If the scan subcommand finds a valid file path as one of the arguments, cdn-proxy will search the file for IPs
or CIDRs and scan each one found. This means you can simply point it to any text file that may contain configuration
data, for example a terraform config file, it will pull out the valid IPs and CIDRs from it for scanning.

Otherwise, if the argument is not a valid file, it should be file or CIDR to be scanned. Multiple arguments can be
passed, as well as types mixed, so IPs, CIDRs, and file paths can all be specified in the same command.


#### Usage

```
Usage: cdn_proxy cloudflare [OPTIONS] COMMAND [ARGS]...

  Manage CloudFlare distributions

Options:
  --token REGION      Sets the AWS region.  [required]
  --zone-name REGION  Sets the AWS region.  [required]
  --help              Show this message and exit.

Commands:
  create  Create a new CloudFront distribution and Lambda@Edge function...
  delete  Disable and delete the specified distribution.
  list    List CloudFront distributions IDs and targets created with...
  scan    HTTP scan of IP's both directly and via proxy...
```

## Burp Suite Extension
The [Burp Suite extension script](./burp_extension/cdn_proxy_burp_ext.py) can be used to proxy traffic through a CloudFront proxy created with cdn-proxy.

### Install
```
git clone https://github.com/RhinoSecurityLabs/cdn-proxy.git
cd cdn-proxy/burp_extension
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

In Burp Extender under the Options tab:
* Make sure the Jython jar location is specified under the Python Environment section.
* In the same section set `Folder for loading modules` to `<location of git repo>/burp_extension/venv/lib/python3.9/site-packages`

In Burp Extender under the Extensions tab:
* Click `Add`
* set `Extension type` to python
* Use `Select file...` to load [cdn_proxy_burp_ext.py](./burp_extension/cdn_proxy_burp_ext.py)
* Click `Next`

In the new CDN Proxy tab that shows up, set the `Proxy Host` field to the domain of the distribution created with
`cdn-proxy cloudflare create`. Traffic from Burp will now be routed through the CloudFront proxy.

## Support

Please [open an issue](https://github.com/RhinoSecurityLabs/cdn-proxy/issues/new) for support.

## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and
[open a pull request](https://github.com/RhinoSecurityLabs/cdn-proxy/compare/).
