from recon.core.module import BaseModule

from censys.search import CensysHosts
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        "name": "Censys - Hosts by Netblock",
        "author": "Censys, Inc. <support@censys.io>",
        "version": 2.1,
        "description": (
            "Retrieves hosts and ports for a neyblock. "
            "Updates the 'hosts' and the 'ports' tables with the results."
        ),
        "query": (
            "SELECT DISTINCT netblock FROM netblocks WHERE netblock IS NOT"
            " NULL"
        ),
        "required_keys": ["censysio_id", "censysio_secret"],
        "options": [
            (
                "virtual_hosts",
                "EXCLUDE",
                False,
                "Whether to include virtual hosts in the results",
            ),
            (
                "per_page",
                "100",
                False,
                "The number of results to return per page",
            ),
            (
                "pages",
                "1",
                False,
                "The number of pages to retrieve",
            ),
        ],
        "dependencies": ["censys>=2.1.2"],
    }

    def module_run(self, netblocks):
        api_id = self.get_key("censysio_id")
        api_secret = self.get_key("censysio_secret")
        c = CensysHosts(api_id, api_secret)
        for netblock in netblocks:
            self.heading(netblock, level=0)
            try:
                query = c.search(
                    f"ip:{netblock}",
                    per_page=int(self.options.get("PER_PAGE", "100")),
                    pages=int(self.options.get("PAGES", "1")),
                    virtual_hosts=self.options.get("VIRTUAL_HOSTS", "EXCLUDE"),
                )
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
