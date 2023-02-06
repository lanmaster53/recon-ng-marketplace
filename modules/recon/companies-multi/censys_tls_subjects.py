from recon.core.module import BaseModule

from censys.search import CensysHosts
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        "name": "Censys - Domains by Company",
        "author": "Censys, Inc. <support@censys.io>",
        "version": 2.1,
        "description": (
            "Retrieves the TLS certificates for a domain. This module queries"
            " the 'services.tls.certificates.leaf_data.subject.organization'"
            " field and updates the 'hosts' and 'ports' tables with the"
            " results."
        ),
        "query": (
            "SELECT DISTINCT company FROM companies WHERE company IS NOT NULL"
        ),
        "required_keys": ["censysio_id", "censysio_secret"],
        "dependencies": ["censys>=2.1.2"],
    }

    def module_run(self, companies):
        api_id = self.get_key("censysio_id")
        api_secret = self.get_key("censysio_secret")
        c = CensysHosts(api_id, api_secret)
        for company in companies:
            company = company.strip('"')
            self.heading(company, level=0)
            try:
                query = c.search(
                    f'services.tls.certificates.leaf_data.subject.organization:"{company}"',
                    virtual_hosts="INCLUDE",
                )
            except CensysException:
                self.print_exception()
                continue
            for hit in query():
                ip = hit["ip"]
                name = hit.get("name")
                if name:
                    self.insert_domains(
                        domain=name, notes="+".join((ip, name))
                    )
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
