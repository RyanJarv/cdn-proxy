package main

import (
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

func main() {
	region := flag.String("region", "", "Proxy domain AWS Region, not used if -proxyDomain is passed")
	profile := flag.String("profile", "", "Proxy domain AWS Profile, not used if -proxyDomain is passed.")
	proxyDomain := flag.String("proxyDomain", "", "The domain to route requests through, fetched from AWS if not specified.")
	workers := flag.Int("workers", 100, "Maximum number of workers used to make requests, defaults to 100.")

	// CloudFlare options
	flag.Parse()

	fmt.Println("Proxy domain: " + *proxyDomain)

	setUlimitOpenFiles(4096)

	reporter := lib.NewReporter()


	if len(flag.Args()) == 0 {
		fmt.Printf("USAGE: %s <cloudflare|cloudfront> [options]", os.Args[0])
		os.Exit(1)
	} else if flag.Args()[0] == "cloudfront" {
		if *proxyDomain == "" {
			proxy, err := cloudfront.GetProxy(context.Background(), *profile, *region)
			if err != nil {
				fmt.Println("error: ", err)
			}
			proxyDomain = proxy.DomainName
		}

		cf := cloudfront.NewScanner(*proxyDomain, *workers, 1000)
		getTargets(flag.Args()[1:], cf.Submit)
		cf.Pool.StopAndWait()
	} else if flag.Args()[0] == "cloudflare" {
		api, err := cloudflareSdk.NewWithAPIToken(os.Getenv("CLOUDFLARE_API_KEY"))
		if err != nil {
			log.Fatalln(err)
		}

		cf := cloudflare.NewScanner(api, reporter, *workers, *proxyDomain, 1000)
		getTargets(flag.Args()[1:], cf.Submit)
		cf.Pool.StopAndWait()
	} else {
		fmt.Println("Must specify either cloudflare or cloudfront as the first argument")
		os.Exit(2)
	}

	json, err := reporter.ToJson()
	if err != nil {
		log.Fatalln(err)
	}

	err = ioutil.WriteFile("./djavan-report.json", json, fs.FileMode(0o0640))
	if err != nil {
		log.Fatalf("writing output: %s\n", err)
	}
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
		file, err := ioutil.ReadFile(v)
		if os.IsNotExist(err) {
			submit(&http.Request{Host: v, URL: &url.URL{Scheme: "http", Host: v, Path: "/"}, Header: map[string][]string{}})
			submit(&http.Request{Host: v, URL: &url.URL{Scheme: "https", Host: v, Path: "/"}, Header: map[string][]string{}})
		} else if err != nil {
			log.Fatalln("unable to read from file: ", err)
		} else {
			targetsFromString(file, submit)
		}
	}
}

func targetsFromString(s []byte, submit func(req *http.Request)) []string {
	regIp, _ := regexp.Compile(`([0-9]{1,3}\.){3}[0-9]{1,3}(?:/\d\d?)`)
	regDomain, _ := regexp.Compile(`\S+.*\.(com|net|io|org)`)

	found := regIp.FindAll(s, math.MaxInt)
	found = append(found, regDomain.FindAll(s, math.MaxInt)...)

	resp := make([]string, 0, 10)
	for _, m := range found {
		if s := string(m); strings.Contains(s, "/") {
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
