# CDN Proxy

Take advantage of IP whitelisting of shared CDNs.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Support](#support)
- [Contributing](#contributing)

## Installation

Currently, you can use pip to install directly from this repo.

```sh
python3 -m venv venv
pip3 install git+ssh://git@github.com/RhinoSecurityLabs/cdn-proxy.git
cdn-proxy --help
```

## Usage

```
Usage: cdn_proxy [OPTIONS] COMMAND [ARGS]...

  Tool for bypassing IP restrictions in origins fronted by shared CDNs.

Options:
  --install-completion [bash|zsh|fish|powershell|pwsh]
                                  Install completion for the specified shell.
  --show-completion [bash|zsh|fish|powershell|pwsh]
                                  Show completion for the specified shell, to
                                  copy it or customize the installation.

  --help                          Show this message and exit.

Commands:
  cloudflare  Manage CloudFlare distributions
  cloudfront  Manage CloudFront distributions
```

### CloudFront

The CloudFront module will set up the distribution for you as well as correctly set the Host header as the request
passes through the CDN. It however is fairly slow and takes a while to set up and teardown.

The X-Forwarded-For header in the request to the origin is randomized for all requests. This will allow bypassing
app side IP based rate limiting in some cases.

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

The CloudFlare module requires an existing zone to exist in the account already. It however is much faster to add/remove
proxies then the CloudFront module.

One shortcoming of this module is that it does not set the host header to the target domain after the request passes
through the CDN. This means this module will only be effective on origins that have a default virtual host set up
hosting the website you're targeting. The enterprise CloudFlare plan does however allow for the host header to be set,
so we may add support for this in the future.

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

## Support

Please [open an issue](https://github.com/RhinoSecurityLabs/cdn-proxy/issues/new) for support.

## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and
[open a pull request](https://github.com/RhinoSecurityLabs/cdn-proxy/compare/).