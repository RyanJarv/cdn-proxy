# CDN Proxy
[![cdn-proxy Tests](https://github.com/RhinoSecurityLabs/cdn-proxy/actions/workflows/python-tests.yml/badge.svg)](https://github.com/RhinoSecurityLabs/cdn-proxy/actions/workflows/python-tests.yml)
[![cdn-scanner Tests](https://github.com/RhinoSecurityLabs/cdn-proxy/actions/workflows/go-tests.yml/badge.svg)](https://github.com/RhinoSecurityLabs/cdn-proxy/actions/workflows/go-tests.yml)

A tool that can be used by web app pentesters to create a copy of the targeted website with CDN and WAF restrictions
disabled.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
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
* You know the origin (backend) IP.
  * [cdn-scanner](#cdn-scanner) can be used to find origins which are only accessible through the CDN network.
* The origin allows access from the Shared IP range used by the CDN network.

Additionally, in the case of CloudFlare, the origin web app uses a default virtual host to serve the website. It should
be possible to perform this attack when this is not the case when you have access to a Enterprise CloudFlare account however
this is not supported by cdn-proxy currently. To do this manually you need to ensure the CloudFlare configuration correctly
sets the host header as the request passes through the CloudFlare network..

## cdn-proxy

### Installation

```sh
pip3 install cdn-proxy
cdn-proxy --help
```

## Usage

The structure for cdn-proxy commands is `cdn-proxy <cloudfront|cloudflare> <create|delete>` where:

The exact process and required options is different between providers, refer to the provider sections below for more details.

### CloudFront

#### Usage

cdn-proxy cloudfront -h

```
Usage: cdn-proxy cloudfront [OPTIONS] COMMAND [ARGS]...

  Manage CloudFront distributions

Options:
  --region REGION    Sets the AWS region.  [default: us-east-1]
  --profile PROFILE  Shared credential profile to use.
  -h, --help         Show this message and exit.

Commands:
  create  Create a new CloudFront distribution and Lambda@Edge function...
  delete  Disable and delete the specified distribution.
  status  Get the status of the CloudFront deployment.
```

#### Overview

The CloudFront module will set up the distribution that acts as a proxy through CloudFront. It is not necessary to
specify a target when using CloudFront and more then one target can be used with the same distribution. This is because
the origin and host header can be set dynamically per request by setting the Cdn-Proxy-Origin and Cdn-Proxy-Host headers
in the client request to the CDN. The X-Forwarded-For header will also be passed through from the client, if this isn't
set it will default to a random IP address in the request to the origin which will allow bypassing app side IP ratelimiting
in some cases.

After deploying the CloudFront configuration with `cdn-proxy cloudfront create` you can navigate to the distribution to find
a help page with more info on headers to control the request as well as some examples.

In addition to making requests manually with curl you can use the CDN Proxy's [Burp Suite Extension](#burp-suite-extension)
to proxy all Burp requests through the CloudFront proxy. Among other things this allows you to browse any sites only exposed
to CloudFront IPs like you normally would through the built in Burp browser.

To scan for origin IPs which only allow requests through the CDN network you can use [cdn-scanner](#cdn-scanner) or the
(less-featured) web based scanner which is hosted at the CloudFront distribution domain name. You will find this domain
name in the output of cdn-proxy after creating the distribution.

Using curl to make a request to a specific origin can be done with the following:

> curl -H 'Cdn-Proxy-Origin: <Origin IP>' <Distribution Domain Name>

Where "<Origin IP>" is the target origin IP and "<Distribution Domain Name>" is the domain name of the CloudFront distribution
created with the `cdn-proxy cloudfront create` command. The domain name can also be found by running `cdn-proxy cloudfront status`.

On the backend CloudFront requires domain names for origins, to work around this the Lambda@Edge function associated with the
distribution that sets the origin dynamically will convert IP address's it finds in the Cdn-Proxy-Origin header to an equivalant
sslip.io subdomain. The sslip.io subdomain will be in the format of `1-1-1-1.sslip.io` and will map to the corresponding IP,
effectively allowing us to use IPs when CloudFront only accepts domain names. This all happens transparently and is mentioned
here for informational purposes.

The CloudFront module also is fairly slow and may take a while to set up and tear down, you however can reuse the same
distribution for any target by changing the `Cdn-Proxy-Origin` header.

### CloudFlare

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

#### Overview

*Warning: Please do not use this on a production domain.*

The CloudFlare subcommand of cdn-proxy is a fair bit simpler then the cloudfront subcommand as it is only used for adding,
removing, and listing proxied DNS records in an already existing domain. It can not create this domain for you and you can
not specify targets dynamically.

This requires an existing domain to already be created in CloudFront, this is because CloudFlare will not assign a temporary
domain to you like CloudFront does. The domain needs to be registered and active, but should be spare domain only used for
cdn-proxy. You will also want to disable all security features on this domain so they do not apply to requests passing through
it.

#### Caveats

One shortcoming of this module is that it does not set the host header to the target domain after the request passes
through the CDN. This means this module will only be effective on origins that do not have a default virtual host set up
hosting the website you're targeting. Setting the host header in the client request will not work as expected since this
will cause the request to be routed to a different CloudFront configuration.

You can work around this limitation if you have an enterprise CloudFlare account. This however is not handled by cdn-proxy
currently, but you can configure this manually using a transform rule in your zone configuration. If you want to see support
for this added to cdn-proxy let us know in a GitHub issue.

## cdn-scanner

### Installation

```sh
GOPRIVATE=github.com/RhinoSecurityLabs/cdn-proxy go install github.com/RhinoSecurityLabs/cdn-proxy
export PATH=$PATH:~/go/bin
cdn-scanner -h
```

## Burp Suite Extension
The [Burp Suite extension script](./burp_extension/cdn_proxy_burp_ext.py) can be used to proxy traffic through a CloudFront proxy created with cdn-proxy.

### Installation
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
