import itertools

from recon.core.module import BaseModule

from censys.search import CensysHosts
from censys.common.exceptions import CensysException


def grouper(n, iterable):
    # via https://stackoverflow.com/a/8991553
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


class Module(BaseModule):
    meta = {
        "name": "Censys - Ports by IP",
        "author": "Censys, Inc. <support@censys.io>",
        "version": 2.1,
        "description": (
            "Retrieves the open ports for each IP address. "
            "Updates the 'ports' table with the results."
        ),
        "query": (
            "SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT"
            " NULL"
        ),
        "required_keys": ["censysio_id", "censysio_secret"],
        "dependencies": ["censys>=2.1.2"],
    }

    def module_run(self, hosts):
        api_id = self.get_key("censysio_id")
        api_secret = self.get_key("censysio_secret")
        c = CensysHosts(api_id, api_secret)
        for ip in hosts:
            ip = ip.strip('"')
            self.heading(ip, level=0)
            try:
                host = c.view(ip)
            except CensysException:
                self.print_exception()
                continue
            for service in host.get("services", []):
                self.insert_ports(
                    ip_address=ip,
                    port=service["port"],
                    protocol=service["transport_protocol"],
                    banner=service.get("banner"),
                    notes=service["service_name"],
                )
