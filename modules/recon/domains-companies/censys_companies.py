from recon.core.module import BaseModule

from censys.search import CensysHosts
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        "name": "Censys - Companies by Domain",
        "author": "Censys, Inc. <support@censys.io>",
        "version": 2.1,
        "description": (
            "Retrieves the TLS certificates for a domain. This module queries"
            " the  'services.tls.certificates.leaf_data.names' field and"
            " updates the 'companies' table with the results."
        ),
        "query": (
            "SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL"
        ),
        "options": [
            (
                "num_buckets",
                "100",
                False,
                "maximum number of buckets to retrieve",
            )
        ],
        "required_keys": ["censysio_id", "censysio_secret"],
        "dependencies": ["censys>=2.1.2"],
    }

    def module_run(self, domains):
        api_id = self.get_key("censysio_id")
        api_secret = self.get_key("censysio_secret")
        c = CensysHosts(api_id, api_secret)
        for domain in domains:
            domain = domain.strip('"')
            self.heading(domain, level=0)
            try:
                report = c.aggregate(
                    "same_service(services.tls.certificates.leaf_data.names:"
                    f" {domain} and"
                    " services.tls.certificates.leaf_data.subject.organization: *)",
                    field="services.tls.certificates.leaf_data.subject.organization",
                    num_buckets=int(self.options.get("NUM_BUCKETS", "100")),
                )
            except CensysException:
                self.print_exception()
                continue
            for bucket in report.get("buckets", []):
                company = bucket.get("key")
                self.insert_companies(
                    company=company, description=f"Domain: {domain}"
                )
