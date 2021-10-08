import json
import re
from typing import List

import CloudFlare as api


class CloudFlare:
    def __init__(self, token, zone_name):
        self.cf = api.CloudFlare(token=token)
        self.zone_name = zone_name
        self.zone_info = self.cf.zones.get(params={"name": self.zone_name})
        self.zone_id = self.zone_info[0]["id"]

    def create(self, target):
        if re.match(r"([0-9]{1,3}\.){3}[0-9]{1,3}", target):
            type = "A"
        else:
            type = "CNAME"

        yield "CloudFront Proxy {} -- Creating records for {}.{}".format(
            target, "cdn-bypass-{}".format(target), self.zone_name
        )
        self.cf.zones.dns_records.post(
            self.zone_id,
            data={
                "name": "cdn-bypass-{}".format(re.sub(r"\.", "-", target)),
                "type": type,
                "content": target,
                "proxied": True,
            },
        )
        yield "CloudFront Proxy {} -- Created".format(target)

    def delete(self, target):
        yield "CloudFront Proxy -- Retrieving records for {}.{}".format(target, self.zone_name)
        dns_records = self.cf.zones.dns_records.get(
            self.zone_id,
            params={
                "name": "cdn-bypass-{}.{}".format(
                    re.sub(r"\.", "-", target), self.zone_name
                ),
            },
        )

        if len(dns_records) == 0:
            print("[ERROR] No proxy found for {}".format(target))
            return
        elif len(dns_records) != 1:
            raise UserWarning("Unexpected number of results")

        self.cf.zones.dns_records.delete(
            self.zone_id,
            dns_records[0]["id"],
        )
        yield "CloudFront Proxy {} -- Deleted".format(target)

    def list(self):
        page = 1
        subdomains: List[dict] = []
        while page == 1 or subdomains:
            subdomains = self.cf.zones.dns_records.get(
                self.zone_id, params={"per_page": 100, "page": page}
            )
            for domain in subdomains:
                if re.match(r"cdn-bypass-.+?\..+", domain["name"]):
                    yield domain["content"], domain["name"]
            page += 1
