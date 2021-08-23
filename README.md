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

If an attacker has the origin IP of an application they may be able to bypass the CDN by making requests to the IP
itself, side stepping any protections that the CDN provides. A common response to this is to IP whitelist the CDN range
on the origin server, preventing these type of CDN bypasses.

This fix however is incomplete, it can be bypassed by setting up a second account on the CDN routing requests to the
same origin. Security protections on this second account can be disabled, sidestepping any protections on the real
account in a similar way to the original issue.

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
