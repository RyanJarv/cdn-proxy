import Container from "react-bootstrap/Container";
import React from "react";

const Help = () => (
    <Container>
        <Container className="title d-flex align-items-center pb-3 mb-5 border-bottom">
            <a href="/" className="d-flex align-items-center text-dark text-decoration-none">
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="32" className="me-2" viewBox="0 0 118 94"
                     role="img">
                    <title>CDN Proxy Help</title>
                    <path
                        fillRule="evenodd"
                        clipRule="evenodd"
                        d="M24.509 0c-6.733 0-11.715 5.893-11.492 12.284.214 6.14-.064 14.092-2.066 20.577C8.943 39.365 5.547 43.485 0 44.014v5.972c5.547.529 8.943 4.649 10.951 11.153 2.002 6.485 2.28 14.437 2.066 20.577C12.794 88.106 17.776 94 24.51 94H93.5c6.733 0 11.714-5.893 11.491-12.284-.214-6.14.064-14.092 2.066-20.577 2.009-6.504 5.396-10.624 10.943-11.153v-5.972c-5.547-.529-8.934-4.649-10.943-11.153-2.002-6.484-2.28-14.437-2.066-20.577C105.214 5.894 100.233 0 93.5 0H24.508zM80 57.863C80 66.663 73.436 72 62.543 72H44a2 2 0 01-2-2V24a2 2 0 012-2h18.437c9.083 0 15.044 4.92 15.044 12.474 0 5.302-4.01 10.049-9.119 10.88v.277C75.317 46.394 80 51.21 80 57.863zM60.521 28.34H49.948v14.934h8.905c6.884 0 10.68-2.772 10.68-7.727 0-4.643-3.264-7.207-9.012-7.207zM49.948 49.2v16.458H60.91c7.167 0 10.964-2.876 10.964-8.281 0-5.406-3.903-8.178-11.425-8.178H49.948z"
                        fill="currentColor"
                    />
                </svg>
                <span className="fs-4">CDN Proxy Help</span>
            </a>
        </Container>
        <h3>Headers</h3>
        <dl className="row">
            <dt className="col-sm-3">Cdn-Proxy-Origin</dt>
            <dd className="col-sm-9">
                <p>
                    The origin the request should be routed to after passing through CloudFront.
                </p>
                <p>
                    This header is Required. If you are seeing this page it is because this header was not
                    included in the request to CloudFront.
                </p>
                <p>
                    You can set this to a hostname or an IP, however because CloudFront only supports hostnames for
                    origins any
                    IP will be replaced with the equivalent domain using <a href="https://sslip.io">sslip.io</a>.
                </p>
            </dd>

            <dt className="col-sm-3">Cdn-Proxy-Host</dt>
            <dd className="col-sm-9">
                <p>
                    Value of the Host header in the request to the origin.
                </p>
                <p>
                    This header is optional but recommended. If not set it will default to the value of
                    Cdn-Proxy-Origin.
                </p>
            </dd>

            <dt className="col-sm-3">X-Forwarded-For</dt>
            <dd className="col-sm-9">
                <p>
                    Passed through to the origin if set (like most other non-listed headers).
                </p>
                <p>
                    If this header is not set it defaults to a randomized IP address in the request to the origin.
                    This allows
                    for bypassing IP based rate limiting in the backend in some cases.
                </p>
                <p>
                    You may also want to try setting this to trusted values such as 127.0.0.1 or another internal IP
                    address to
                    expose any administrative or debug pages restricted by IP in the web application (compared to
                    restrictions
                    enforced in CloudFront/WAF, which will already be disabled when using this proxy).
                </p>
                <p>
                    Multiple caching proxies are sometimes used in front of the origin, say CloudFront routes to
                    Varnish which
                    routes to nginx. In cases like this, where you are using the nginx service as the origin, you
                    may need to
                    set the target IP you want to add multiple IPs to this header with the one you want to spoof on
                    the far
                    left (example: X-Forwarded-For: 127.0.0.1, 172.32.10.10). It's also possible the second IP here
                    needs to be
                    a trusted IP on the internal network of the origin.
                </p>
            </dd>
        </dl>

        <hr className="col-3 col-md-2 mb-5"/>

        <h3>Examples</h3>
        <dl className="row">
            <dt className="col-sm-3">Curl -- No Host Header</dt>
            <dd className="col-sm-9">
                <p>
                    Here we are simply forwarding to the public ifconfig.me service after the request passes
                    through CloudFront.
                    The IP returned will be the source IP our request made from the CloudFront network. We don't
                    need to set
                    Cdn-Proxy-Host because ifconfig.me responds the same regardless of what the host header is
                    set to.
                </p>
                <pre><code className="example">
curl -H 'Cdn-Proxy-Origin: ifconfig.me' -H 'Cdn-Proxy-Host: ifconfig.me' XXXXXXXXXXXXX.cloudfront.net
                    </code></pre>
            </dd>
            <dt className="col-sm-3">Curl -- EC2 Origin</dt>
            <dd className="col-sm-9">
                <p>
                    More likely you'll be running something like this, where Cdn-Proxy-Origin is a specific
                    backend server and
                    Cdn-Proxy-Host is the domain name of the website it is running. If Cdn-Proxy-Host is not set
                    correctly you
                    may not be able to reach the site, but this depends on the server configuration.
                </p>
                <pre><code className="example">
            curl -H 'Cdn-Proxy-Origin: ec2-XX-XX-XX-XX.us-west-2.compute.amazonaws.com' -H 'Cdn-Proxy-Host: example.com' XXXXXXXXXXXXX.cloudfront.net
                    </code></pre>
                </dd>
            </dl>
    </Container>
);

export default Help;