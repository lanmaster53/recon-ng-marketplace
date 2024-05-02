from recon.core.module import BaseModule

from censys.search import CensysHosts
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        "name": "Censys - Hosts by Search Query",
        "author": "Censys, Inc. <support@censys.io>",
        "version": 2.1,
        "description": (
            "Retrieves details for hosts matching an arbitrary Censys query."
            " Updates the 'hosts', 'domains', and 'ports' tables with the"
            " results."
        ),
        "required_keys": ["censysio_id", "censysio_secret"],
        "options": [
            (
                "censys_query",
                'services.http.response.html_title: "Welcome to recon-ng"',
                True,
                "The Censys Search Query to execute",
            ),
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

    def module_run(self):
        api_id = self.get_key("censysio_id")
        api_secret = self.get_key("censysio_secret")
        c = CensysHosts(api_id, api_secret)
        try:
            query = c.search(
                self.options["CENSYS_QUERY"],
                per_page=int(self.options.get("PER_PAGE", "100")),
                pages=int(self.options.get("PAGES", "1")),
                virtual_hosts=self.options.get("VIRTUAL_HOSTS", "EXCLUDE"),
            )
        except CensysException:
            self.print_exception()
            return
        for hit in query():
            ip = hit["ip"]
            name = hit.get("name")
            if name:
                self.insert_domains(domain=name, notes="+".join((ip, name)))
            common_kwargs = {
                "ip_address": ip,
                "host": name,
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
