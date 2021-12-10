package cloudflare

import (
	"bytes"
	"context"
	"crypto/tls"
	"fmt"
	"github.com/RhinoSecurityLabs/cdn-proxy/lib"
	"github.com/alitto/pond"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/cloudflare/cloudflare-go"
	"io/ioutil"
	"log"
	"net"
	"net/http"
	"strings"
	"time"
)

type SvcState string

const (
	SvcStateOpen = "open"
	SvcStateAccessDenied = "access denied"
	SvcStateClosed = "closed"
	SvcStateFiltered = "filtered"
	SvcStateUnknown = "unknown"
	SvcStateProxyError = "proxy error"
	dnsResolverIP        = "1.1.1.1:53" // Google DNS resolver.
	dnsResolverProto     = "udp"        // Protocol to use for the DNS resolver
	dnsResolverTimeoutMs = 1000         // Timeout (ms) for the DNS resolver (optional)
)


func (s SvcState) IsBlocked() bool {
	if s == SvcStateClosed || s == SvcStateAccessDenied {
		return true
	} else {
		return false
	}
}

func GetProxy(api *cloudflare.API, domain string) (string, error) {
	// Fetch the zone ID
	id, err := api.ZoneIDByName(domain) // Assuming example.com exists in your Cloudflare account already
	if err != nil {
		return "", err
	}
	return id, nil
}

func NewScanner(api *cloudflare.API, reporter lib.Reporter, maxWorkers int, domain string, maxCapacity int) *CloudFlareScanner {
	zoneId, err := GetProxy(api, domain)
	if err != nil {
		log.Fatalln(err)
	}

	// simple incrementor for concurrent access (is this needed?)
	incr := make(chan int, 10)
	go func() {
		for {
			// Maximum # of records seems to be around 800.
			for i := 1; i < 500; i++ {
				incr <- i
			}
		}
	}()


	// Set up custom DNS resolver that uses 1.1.1.1
	dialer := &net.Dialer{
		FallbackDelay: time.Millisecond * 300,
		Resolver: &net.Resolver{
			PreferGo: true,
			Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
				d := net.Dialer{
					FallbackDelay: time.Millisecond * 300,
					Timeout: time.Duration(dnsResolverTimeoutMs) * time.Millisecond,
				}
				return d.DialContext(ctx, dnsResolverProto, dnsResolverIP)
			},
		},
	}
	dialContext := func(ctx context.Context, network, addr string) (net.Conn, error) {
		return dialer.DialContext(ctx, network, addr)
	}

	return &CloudFlareScanner{
		api:        api,
		zoneId:     zoneId,
		domain:     domain,
		report:     reporter,
		Pool:       pond.New(maxWorkers, maxCapacity),
		domainIncr: incr,
		Client: &http.Client{
			Transport: &http.Transport{
				DialContext: dialContext,
				TLSClientConfig:        &tls.Config{
					InsecureSkipVerify: true,
					CipherSuites:       lib.AllCiphers,
					MinVersion:         0,
				},
			},
			CheckRedirect: lib.NoRedirects,
			// Timeout should be at least the amount of time it takes CloudFlare to return a specific error code.
			// This could be set to something smaller for direct requests.
			Timeout: time.Second * 40,
		},
	}
}

type CloudFlareScanner struct {
	zoneId     string
	Client     *http.Client
	Pool       *pond.WorkerPool
	domainIncr chan int
	api        *cloudflare.API
	domain string
	report lib.Reporter
}

type Response struct {
	ProxyResp  *http.Response
	ProxyErr   error
	DirectResp *http.Response
	DirectErr  error
}

func (c *CloudFlareScanner) Submit(req *http.Request) {
	c.Pool.Submit(func() {
		var dCode, pCode int

		pResp, pState, pErr := c.handleProxyRequest(context.Background(), req)
		if pResp != nil {
			pCode = pResp.StatusCode
		}

		dResp, dState, dErr := c.handleDirectRequest(req)
		if dResp != nil {
			dCode = dResp.StatusCode
		}

		var msg string
		if req.Host == req.URL.Host {
			msg = fmt.Sprintf("%s://%s -- ", req.URL.Scheme, req.Host)
		} else {
			msg = fmt.Sprintf("%s (Host: %s) -- ", req.Host, req.URL.Host)
		}

		if pCode == 502 && dErr != nil && strings.Contains(dErr.Error(), "remote error: tls: handshake failure") {
			fmt.Println(msg + "origin tls handshake failure")
			return
		}

		// Add proxy bypasses to the report.
		if pState == SvcStateOpen &&
			(dState == SvcStateClosed || dState == SvcStateFiltered || dState == SvcStateAccessDenied) {
			if pCode <= 200 && pCode <= 299 {
				c.report.Add("cloudflare_proxy_bypass", lib.Finding{
					ResourceType:     "CloudFlare Proxy Bypass",
					GlobalIdentifier: req.URL.String(),
				})
			} else {
				// If the status code is not 2XX this most likely (but not necessarily) means the Host header is not
				// set correctly. This is still a risk but means the attacker would have to have access to an
				// enterprise CloudFlare account, which allows you to arbitrarily set the header as it passes through
				// the CDN network.
				//
				// Notes:
				//   * Some sites will show a redirect for the root URL but then allow any host header value for
				//     sensitive pages. One common example of this is WordPress.
				//   * If a redirect includes the name used for the host header then it should qualify as a full
				//     bypass.
				//
				// TODO: Improve detection of full proxy bypasses (second note, and maybe the first above).
				//
				c.report.Add("cloudflare_partial_proxy_bypass", lib.Finding{
					ResourceType:     "Partial CloudFlare Proxy Bypass",
					GlobalIdentifier: req.URL.String(),
				})
			}
		} else if pState == SvcStateOpen && dState == SvcStateOpen {
			c.report.Add("publicly_exposed_http_service", lib.Finding{
				ResourceType:     "Publicly Exposed HTTP Service",
				GlobalIdentifier: req.URL.String(),
			})
		}

		if pState == dState && (pErr == dErr || pErr.Error() == dErr.Error()) {
			if pErr != nil {
				msg += fmt.Sprintf("Both: %s (%d -- %s)", pState, pCode, pErr)
			} else {
				msg += fmt.Sprintf("Both: %s (%d)", pState, pCode)
			}
		} else {
			if pErr != nil {
				msg += fmt.Sprintf("Via Proxy: %s (%d -- %s)", pState, pCode, pErr)
			} else {
				msg += fmt.Sprintf("Via Proxy: %s (%d)", pState, pCode)
			}

			if dErr != nil {
				if dResp == nil {
					msg += fmt.Sprintf(", Origin: error (000 -- %s)", dErr)
				} else {
					msg += fmt.Sprintf(", Origin: %s (%d -- %s)", dState, dCode, dErr)
				}
			} else {
				msg += fmt.Sprintf(", Origin: %s (%d)", dState, dCode)
			}
		}

		if pState == SvcStateOpen && dState.IsBlocked() {
			headers := ""
			for k, v := range pResp.Header {
				for _, v2 := range v {
					headers += fmt.Sprintf(" %s: %s\n", k, v2)
				}
			}
			all, err := ioutil.ReadAll(pResp.Body)
			if err != nil {
				fmt.Println("failed reading body of response")
			}
			fmt.Println("\n" + msg, "-- Bypass Found!", "\n" + headers, "\n" + string(all[:200]) + "\n")
		} else {
			fmt.Println(msg)
		}
	})
}

func (c *CloudFlareScanner) handleDirectRequest(req *http.Request) (*http.Response, SvcState, error) {
	resp, err := c.Client.Do(req)

	var state SvcState
	if resp == nil {
		if strings.Contains(err.Error(), "Client.Timeout exceeded while awaiting headers") {
			state = SvcStateFiltered
			err = nil
		} else if strings.Contains(err.Error(), "connect: connection refused") {
			state = SvcStateClosed
			err = nil
		} else {
			state = SvcStateUnknown
		}
	} else {
		switch c := resp.StatusCode; {
		case c == 403:
			state = SvcStateAccessDenied
		case c == 301 || c == 302 || c == 307:
			state = SvcStateOpen
			err = fmt.Errorf("%s", resp.Header.Get("Location"))
		case 100 <= c && c <= 599:
			state = SvcStateOpen
		default:
			state = SvcStateUnknown
			err = fmt.Errorf("unknown status code: %d", c)
		}
	}
	return resp, state, err
}

func (c *CloudFlareScanner) handleProxyRequest(ctx context.Context, req *http.Request) (*http.Response, SvcState, error) {
	r := req.Clone(context.Background())

	// TODO: Handle setting host header on origin requests when the user has a enterprise account.
	subdomain := fmt.Sprintf("proxy-%02d", <-c.domainIncr)

	proxyDomain := fmt.Sprintf("%s.%s", subdomain, c.domain)
	rr := cloudflare.DNSRecord{
		Name:   proxyDomain,
		ZoneID: c.zoneId,
	}

	records, err := c.api.DNSRecords(ctx, c.zoneId, rr)
	if err != nil {
		return nil, "", fmt.Errorf("retrieving dns record for %s: %w", subdomain, err)
	}


	rr.Type = "CNAME"
	rr.Content = r.Host
	rr.Proxied = aws.Bool(true) // Might as well reuse aws pointer functions here.
	rr.TTL = 0
	for _, record := range records {
		err := c.api.DeleteDNSRecord(ctx, c.zoneId, record.ID)
		if err != nil {
			return nil, "", fmt.Errorf("%s: %w", subdomain, err)
		}
	}

	// The real host for this request is the CloudFront proxy, and the host header should match this.
	r.Host = proxyDomain
	r.URL.Host = proxyDomain

	var completed = false
	var resp *http.Response
	for i := 0; i < 30; i++ {
		resp, err = c.Client.Do(r)

		// We can continue if the DNS lookup fails. This will most likely happen on the first run.
		if err != nil && strings.Contains(err.Error(), "no such host") {
			completed = true
			break
		}

		if resp != nil {
			b, err := ioutil.ReadAll(resp.Body)
			if err == nil {
				// We can also continue if the CloudFlare is reporting the domain is not configured.
				if resp.StatusCode == 530 && bytes.Contains(b, []byte("Origin DNS error")) {
					completed = true
					break
				}
			}
		}
		time.Sleep(time.Second * 5)
	}
	if !completed {
		return nil, SvcStateUnknown, err
	}

	_, err = c.api.CreateDNSRecord(context.Background(), c.zoneId, rr)
	if err != nil {
		return nil, "", fmt.Errorf("creating record for %s: %w", subdomain, err)
	}


	completed = false
	for i := 0; i < 20; i++ {
		//fmt.Printf("+")
		resp, err = c.Client.Do(r)
		if resp != nil && !(resp.StatusCode == 530) {
			completed = true
			break
		}
		time.Sleep(time.Second * 5)
	}
	if !completed {
		return nil, SvcStateUnknown, err
	}

	var state SvcState
	if resp == nil {
		if strings.Contains(err.Error(), "Client.Timeout exceeded while awaiting headers") {
			state = SvcStateProxyError
		} else if err != nil && strings.Contains(err.Error(), "no redirects") {
			state = SvcStateOpen
			err = fmt.Errorf("%s", resp.Header.Get("Location"))
		} else {
			state = SvcStateUnknown
		}
	} else {
		switch c := resp.StatusCode; {
		case c == 530:
			fmt.Println(c)
			state = SvcStateUnknown
		case c == 403:
			state = SvcStateAccessDenied
		case c == 521:
			state = SvcStateClosed
		case c == 522 || c == 523:
			state = SvcStateFiltered
		case c == 301 || c == 302 || c == 307:
			state = SvcStateOpen
			err = fmt.Errorf("%s", resp.Header.Get("Location"))
		case 200 <= c && c <= 599:
			state = SvcStateOpen
		default:
			state = SvcStateUnknown
			err = fmt.Errorf("unknown status code: %d", c)
		}
	}

	return resp, state, err
}
