import {Address4} from "ip-address";


export class CloudFrontScanner {
  readonly hostnames: Array<string>;
  readonly cdnProxy: string;

  constructor(cdnProxy: string, hostnames: Array<string> = []) {
    this.cdnProxy = cdnProxy;

    if (hostnames.length > 1) {
      throw 'Using more then one hostname is not supported currently!'
    }
    this.hostnames = hostnames;
  }


  // TODO: We'll actually be passing a list of ips/dns records, along with preconfigured path, scheme, and list of
  //  host headers. Only one host header is supported now, but later this list will include hosts we want to test for
  //  each ip/domain and scheme combination. This allows for brute forcing the domain when we have several we might be
  //  expecting.
  public request(backendHost: string) {
    let hdrs = new Headers({
      'Cdn-Proxy-Origin': backendHost,
    })

    if (this.hostnames.length > 0) {
      hdrs.set('Cdn-Proxy-Host', this.hostnames[0])
    } else {
      hdrs.set('Cdn-Proxy-Host', backendHost)
    }

    fetch(this.cdnProxy, {headers: hdrs})
        .then(resp => console.log(resp.body))
  }

  public scan(backends: Array<string>) {
    for (const i in backends) {
      this.request(backends[i])
    }
  }
}


export function textToIps(input: string): Array<string> {
  let addr: Address4 = new Address4(input)

  // Not sure why they use BigInt here, more then enough numbers to hold an IPv4 address
  let start = Number(addr.startAddress().bigInteger())
  let end = Number(addr.endAddress().bigInteger())
  let numIps = (end - start)

  // While typically the first and last IPs of a CIDR aren't used, the CIDR input here will likely not map to the real
  // CIDR used for thee network at the destination.
  let ips = []
  for (let i = 0; i <= numIps; i++) {
    ips.push(Address4.fromInteger(start + i).correctForm())
  }
  return ips
}