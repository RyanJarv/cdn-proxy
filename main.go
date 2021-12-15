package main

import (
	"bytes"
	"context"
	"encoding/binary"
	"flag"
	"fmt"
	"github.com/RhinoSecurityLabs/cdn-proxy/lib"
	"github.com/RhinoSecurityLabs/cdn-proxy/pkg/cloudflare"
	"github.com/RhinoSecurityLabs/cdn-proxy/pkg/cloudfront"
	cloudflareSdk "github.com/cloudflare/cloudflare-go"
	"io/fs"
	"io/ioutil"
	"log"
	"math"
	"net"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
	"syscall"
)

var (
	workers = flag.Int("workers", 100, "Maximum number of workers used to make requests, defaults to 100.")
	domain = flag.String("domain", "", "The domain to route requests through, fetched from AWS if not specified.")
	report = flag.String("report", "", "JSON report file output location.")

	cloudfrontCmd = flag.NewFlagSet("cloudfront", flag.ExitOnError)
	cloudflareCmd = flag.NewFlagSet("cloudflare", flag.ExitOnError)

	region = cloudfrontCmd.String("region", "", "Proxy domain AWS Region, not used if -proxyDomain is passed")
	profile = cloudfrontCmd.String("profile", "", "Proxy domain AWS Profile, not used if -proxyDomain is passed.")


	subcommands = map[string]*flag.FlagSet{
		cloudfrontCmd.Name(): cloudfrontCmd,
		cloudflareCmd.Name(): cloudflareCmd,
	}
)


func main() {
	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage of cdn-scanner: %s [-domain string] [-report string] [-workers int] "+
			"<cloudfront|cloudflare> [args...] <IP/CIDR/Path to File> ...\n", os.Args[0])

		flag.PrintDefaults()
		fmt.Printf(`

Overview

	The cloudflare or cloudfront subcommands both take a list of IPs, Hostnames, CIDRs or optionally files which in turn
	should contain a list of additional IPs, Hostnames, or CIDRs. Each network asset is then scanned, once for http and once
	for https, both directly as well as proxied through the CDN specified, the responses are then compared to determine
	whether IP allow listing is in effect for the asset.

	For example, if the TCP connection for direct http request responds is closed by the remote host and the request when
	proxied through the CDN responds with a 200 then this would indicate IP allow listing is used on the scanned asset.

Example output

		******************************************************************

		 http://1.2.3.4 -- Both: open (200)

		******************************************************************

		 https://1.2.3.5 -- Via Proxy: filtered (504), Origin: closed (0)

		******************************************************************

	In the output above the first line indicates that port 80 (http) at the address 1.2.3.4 is accessible both from
	the scanners current IP as well as from the source IP of the CDN used.

	The second line indicates that port 443 (https) at the address 1.2.3.5 was filtered (did not respond) when accessed
	through the proxy and when accessed directly the remote closed (remote rejected the connection) the connection.

	The status (open/closed/filtered) when for the proxied request is determined by the HTTP status code returned by the
	CDN the request was proxied through. Typically CDNs will have different 5XX error codes for various failure
	conditions which should allow you to determine if the remote rejected the connection, didn't respond, or timed out
	in some other way. Worth keeping in mind that associating these HTTP status codes with the correct state is a work
	in progress currently.

	Generally the interesting results you likely want to look for will be when the proxied request returns a 2XX status
	code and the direct request either is closed, filtered, or denied access (403). This very likely means there is
	IP allow listing in place on the origin and that you can bypass this by routing requests through a distribution you
	control in the CDN.

`)

		cloudfrontUsage := getDefaults(cloudfrontCmd).String()
		cloudfrontUsage = strings.ReplaceAll(cloudfrontUsage, "\n", "\n\t\t")

		cloudflareUsage := getDefaults(cloudflareCmd).String()
		cloudflareUsage = strings.ReplaceAll(cloudflareUsage, "\n", "\n\t\t")

		fmt.Printf(`
Sub Commands
	cloudfront [IP/Hostname/CIDR/file path] ...

		%s
		
		The cloudfront subcommand assumes the value passed with -domain is a cloudfront distribution set up with
		cdn-proxy. If -domain is not passed then cdn-scanner will attempt to look for a CloudFront distribution in the
		current account created by cdn-proxy.

		The origin configuration is set dynamically for each request, making the CloudFront scanner much faster then
		the cloudflare one.

	cloudflare [IP/Hostname/CIDR/file path] ...

	    Note: Access keys need are assumed to be in the environment variables CLOUDFLARE_API_KEY and CLOUDFLARE_API_EMAIL.
		
		The CloudFlare scanner works a bit differently, it does not necessarily need anything set up by cdn-proxy. This
		scanner only needs access to a spare CloudFlare zone. Please use a spare, rather then risking running this
		on any important domain.

		Each network address first adds a proxied DNS subdomain to the zone passed in the -domain option. It then
		makes a request to the recently created subdomain as well as to the network address directly comparing the two
		responses.

		After some time the subdomains will start getting reused, because it's difficult to know exactly when a change
		to the CloudFlare API has gone into effect it is necessary to peform several steps which slow this scan down
		quite a bit. First the subdomain that will be rotated is deleted from CloudFlare and we wait for either
		CloudFlare to start returning the appropriate error message or for DNS to fail. Once the subdomain has
		successfully been deleted it is then created again withh the new updated record. The proxied request then can
		be served once the subdomain is observed to start working again. So far this has been the most reilable method
		found, without these steps the results eventually become out of sync with the state the CloudFlare network was
		in when the request is made. This typically doesn't happen at first, but rather after the scan has run for some
		time suggesting that the CloudFlare API may start queing requests for individual users after some threshold.
		

		%s

`, cloudfrontUsage, cloudflareUsage)
	}


	flag.Parse()

	if flag.NArg() < 1 {
		log.Fatalln("Expected either cloudflare or cloudfront subcommands.")
	}

	cmd := subcommands[flag.Args()[0]]
	if cmd == nil {
		fmt.Println("Expected either cloudflare or cloudfront subcommands.")
		os.Exit(1)
	}

	err := cmd.Parse(flag.Args()[1:])
	if err != nil {
		log.Fatalln(err)
	}

	setUlimitOpenFiles(4096)
	reporter := lib.NewReporter()

	switch cmd.Name() {
	case "cloudfront":
		if *domain == "" {
			proxy, err := cloudfront.GetProxy(context.Background(), *profile, *region)
			if err != nil {
				fmt.Println("error: ", err)
			}
			domain = proxy.DomainName
		}

		cf := cloudfront.NewScanner(*domain, *workers, 1000)
		getTargets(flag.Args()[1:], cf.Submit)
		cf.Pool.StopAndWait()
	case "cloudflare":
		api, err := cloudflareSdk.NewWithAPIToken(os.Getenv("CLOUDFLARE_API_KEY"))
		if err != nil {
			log.Fatalln(err)
		}

		cf := cloudflare.NewScanner(api, reporter, *workers, *domain, 1000)
		getTargets(flag.Args()[1:], cf.Submit)
		cf.Pool.StopAndWait()
	default:
		fmt.Println("Expected either cloudflare or cloudfront subcommands.")
		os.Exit(2)
	}

	if report != nil && *report != "" {
		json, err := reporter.ToJson()
		if err != nil {
			log.Fatalln(err)
		}

		err = ioutil.WriteFile(*report, json, fs.FileMode(0o0640))
		if err != nil {
			log.Fatalf("JSON report location: %s\n", err)
		}
	}
}

func getDefaults(cmd *flag.FlagSet) *bytes.Buffer {
	buf := new(bytes.Buffer)
	cmd.SetOutput(buf)
	cmd.PrintDefaults()
	return buf
}

func setUlimitOpenFiles(i uint64) {
	var rLimit syscall.Rlimit
	err := syscall.Getrlimit(syscall.RLIMIT_NOFILE, &rLimit)
	if err != nil {
		fmt.Println("Error Getting Rlimit ", err)
	}

	if rLimit.Cur >= i {
		fmt.Println("Ulimit # of files open is currently set to", rLimit.Cur)
		return
	}

	if rLimit.Max > i {
		fmt.Println("Ulimit max # of files open is less then", i, "raising this value may fail if the current " +
		"user does not have permissions to override this value.")
	}
	rLimit.Cur = i
	err = syscall.Setrlimit(syscall.RLIMIT_NOFILE, &rLimit)
	if err != nil {
		fmt.Println("error setting Rlimit ", err)
	}
}

func getTargets(args []string, submit func(req *http.Request)) {
	for _, v := range args {
		content, err := ioutil.ReadFile(v)
		if os.IsNotExist(err) {
			submit(&http.Request{Host: v, URL: &url.URL{Scheme: "http", Host: v, Path: "/"}, Header: map[string][]string{}})
			submit(&http.Request{Host: v, URL: &url.URL{Scheme: "https", Host: v, Path: "/"}, Header: map[string][]string{}})
		} else if err != nil {
			log.Fatalln("unable to read from file: ", err)
		} else {
			fmt.Printf("Reading contents of %s\n", v)
			targetsFromString(content, submit)
		}
	}
}

func targetsFromString(s []byte, submit func(req *http.Request)) []string {
	regIp, _ := regexp.Compile(`([0-9]{1,3}\.){3}[0-9]{1,3}(?:/\d\d?)?`)
	regDomain, _ := regexp.Compile(`\S+.*\.(com|net|io|org)`)

	found := regIp.FindAll(s, math.MaxInt)
	found = append(found, regDomain.FindAll(s, math.MaxInt)...)

	resp := make([]string, 0, 10)
	for _, m := range found {
		if s := string(m); strings.HasSuffix(s, "/") {
			ips, err := cidrToIps(s)
			if err != nil {
				log.Fatalln(err)
			}
			for _, ip := range ips {
				submit(&http.Request{Host: ip, URL: &url.URL{Scheme: "http", Host: ip, Path: "/"}, Header: map[string][]string{}})
				submit(&http.Request{Host: ip, URL: &url.URL{Scheme: "https", Host: ip, Path: "/"}, Header: map[string][]string{}})
			}
		} else {
			submit(&http.Request{Host: s, URL: &url.URL{Scheme: "http", Host: s, Path: "/"}, Header: map[string][]string{}})
			submit(&http.Request{Host: s, URL: &url.URL{Scheme: "https", Host: s, Path: "/"}, Header: map[string][]string{}})
		}
	}
	return resp
}

func cidrToIps(cidr string) ([]string, error) {
	_, ipv4Net, err := net.ParseCIDR(cidr)
	if err != nil {
		return []string{}, fmt.Errorf("error parsing cidr %s: %s", cidr, err)
	}

	// convert IPNet struct mask and address to uint32
	// network is BigEndian
	mask := binary.BigEndian.Uint32(ipv4Net.Mask)
	start := binary.BigEndian.Uint32(ipv4Net.IP)

	// find the final address
	finish := (start & mask) | (mask ^ 0xffffffff)

	resp := make([]string, 0, finish)
	// loop through addresses as uint32
	for i := start; i <= finish; i++ {
		// convert back to net.IP
		ip := make(net.IP, 4)
		binary.BigEndian.PutUint32(ip, i)
		resp = append(resp, ip.String())
	}

	return resp, nil
}
