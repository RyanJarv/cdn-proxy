package cloudfront

import (
	"context"
	"crypto/tls"
	"fmt"
	"github.com/RhinoSecurityLabs/cdn-proxy/lib"
	"github.com/alitto/pond"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/cloudfront"
	"github.com/aws/aws-sdk-go-v2/service/cloudfront/types"
	"io/ioutil"
	"log"
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
)

func (s SvcState) IsBlocked() bool {
	if s == SvcStateClosed || s == SvcStateAccessDenied {
		return true
	} else {
		return false
	}
}

// GetProxy returns the CloudFront distribution created by cdn-proxy otherwise nil if none are found.
// CloudFront distributions created by cdn-proxy are identified by a Tag key of "cdn-proxy-target".
func GetProxy(ctx context.Context, profile, region string) (*types.DistributionSummary, error) {
	cfg, err := config.LoadDefaultConfig(ctx, config.WithRegion(region), config.WithSharedConfigProfile(profile))
	if err != nil {
		log.Fatalf("unable to load SDK config, %v", err)
	}

	// Using the Config value, create the DynamoDB Client
	svc := cloudfront.NewFromConfig(cfg)


	p := cloudfront.NewListDistributionsPaginator(svc, &cloudfront.ListDistributionsInput{})
	for p.HasMorePages() {
		page, err := p.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to get a page, %w", err)
		}

		for _, dist := range page.DistributionList.Items {
			resp, err := svc.ListTagsForResource(ctx, &cloudfront.ListTagsForResourceInput{
				Resource: dist.ARN,
			})
			if err != nil {
				return nil, fmt.Errorf("unable to list tags for resource %s: %w", *dist.ARN, err)
			}
			for _, v := range resp.Tags.Items {
				if *v.Key == "cdn-proxy-target" {
					return &dist, nil
				}
			}
		}
	}
	return nil, nil
}

func NewScanner(proxyDomain string, maxWorkers, maxCapacity int) *CloudFrontScanner {
	return &CloudFrontScanner{
		ProxyDomain: proxyDomain,
		Pool:        pond.New(maxWorkers, maxCapacity),
		Client: &http.Client{
			Transport: &http.Transport{
				TLSClientConfig: &tls.Config{
					InsecureSkipVerify: true,
					CipherSuites:       lib.AllCiphers,
					MinVersion:         0,
				},
			},
			CheckRedirect: lib.NoRedirects,
			Timeout: time.Second * 15,
		},
	}
}

type CloudFrontScanner struct {
	ProxyDomain string
	Client      *http.Client
	Pool        *pond.WorkerPool
}

type Response struct {
	ProxyResp  *http.Response
	ProxyErr   error
	DirectResp *http.Response
	DirectErr  error
}

func (c *CloudFrontScanner) Submit(req *http.Request) {
	c.Pool.Submit(func() {
		var dCode, pCode int

		pResp, pState, pErr := c.handleProxyRequest(req)
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

		if pState == dState && pCode == dCode && (pErr == dErr || pErr.Error() == dErr.Error()) {
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

func (c *CloudFrontScanner) handleDirectRequest(req *http.Request) (*http.Response, SvcState, error) {
	resp, err := c.Client.Do(req)

	var state SvcState
	if resp == nil {
		if strings.Contains(err.Error(), "Client.Timeout exceeded while awaiting headers") {
			state = SvcStateClosed
			err = nil
		} else {
			state = SvcStateUnknown
		}
	} else {
		switch c := resp.StatusCode; {
		case c == 403:
			state = SvcStateAccessDenied
		case c == 301 || c == 302:
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

func (c *CloudFrontScanner) handleProxyRequest(req *http.Request) (*http.Response, SvcState, error) {
	r := req.Clone(context.Background())
	if (req.Header.Get("Cdn-Proxy-Origin") != "") || (r.Header.Get("Cdn-Proxy-Host") != "") {
		return nil, SvcStateUnknown, fmt.Errorf("Cdn-Proxy-Origin and Cdn-Proxy-Host are not allowed on requests")
	}
	// Cdn-Proxy-Origin is the host the request should be sent to after passing through the proxy.
	r.Header.Add("Cdn-Proxy-Origin", r.Host)

	// Cdn-Proxy-Host is what the host header should be set to when being sent to the origin.
	r.Header.Add("Cdn-Proxy-Host", r.URL.Host)

	// The real host for this request is the CloudFront proxy, and the host header should match this.
	r.Host = c.ProxyDomain
	r.URL.Host = c.ProxyDomain

	resp, err := c.Client.Do(r)

	var state SvcState
	if resp == nil {
		if strings.Contains(err.Error(), "Client.Timeout exceeded while awaiting headers") {
			  state = SvcStateProxyError
		} else {
			  state = SvcStateUnknown
		}
	} else {
		switch c := resp.StatusCode; {
		case c == 403:
			state = SvcStateAccessDenied
		case c == 502:
			 state = SvcStateClosed
		case c == 504:
			state = SvcStateFiltered
		case c == 301 || c == 302:
			state = SvcStateOpen
			err = fmt.Errorf("%s", resp.Header.Get("Location"))
		case 200 <= c && c <= 499:
			state = SvcStateOpen
		default:
			state = SvcStateUnknown
			err = fmt.Errorf("unknown status code: %d", c)
		}
	}

	return resp, state, err
}
