from recon.core.module import BaseModule

from censys.search import CensysHosts
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        "name": "Censys - Hosts by Hostname",
        "author": "Censys, Inc. <support@censys.io>",
        "version": 2.1,
        "description": (
            "Retrieves all IPs for a given hostname. This module queries the"
            " 'name' field and updates the 'hosts' and 'ports' tables with the"
            " results."
        ),
        "query": "SELECT DISTINCT host FROM hosts WHERE host IS NOT NULL",
        "required_keys": ["censysio_id", "censysio_secret"],
        "dependencies": ["censys>=2.1.2"],
    }

    def module_run(self, hosts):
        api_id = self.get_key("censysio_id")
        api_secret = self.get_key("censysio_secret")
        c = CensysHosts(api_id, api_secret)
        for host in hosts:
            host = host.strip('"')
            self.heading(host, level=0)
            try:
                query = c.search(f"name:{host}", virtual_hosts="ONLY")
            except CensysException:
                self.print_exception()
                continue
            for hit in query():
                common_kwargs = {
                    "ip_address": hit["ip"],
                    "host": hit.get("name"),
                }
                location = hit.get("location", {})
                coords = location.get("coordinates", {})
                self.insert_hosts(
                    region=location.get("continent"),
                    country=location.get("country"),
                    latitude=coords.get("latitude"),
                    longitude=coords.get("longitude"),
                    **common_kwargs,
                )
                for service in hit.get("services", []):
                    self.insert_ports(
                        port=service["port"],
                        protocol=service["transport_protocol"],
                        notes=service["service_name"],
                        **common_kwargs,
                    )
