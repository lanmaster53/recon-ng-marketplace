from recon.core.module import BaseModule

from censys.search import CensysHosts
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        "name": "Censys - Domains by Email",
        "author": "Censys, Inc. <support@censys.io>",
        "version": 2.1,
        "description": (
            "Retrieves domains from the TLS certificates for an email address."
            " This module queries the 'parsed.subject.email_address' field and"
            " updates the 'domains' table with the results."
        ),
        "query": "SELECT DISTINCT email FROM contacts WHERE email IS NOT NULL",
        "options": [
            ("num_buckets", 100, True, "maximum number of buckets to retrieve")
        ],
        "required_keys": ["censysio_id", "censysio_secret"],
        "dependencies": ["censys>=2.1.2"],
    }

    def module_run(self, emails):
        api_id = self.get_key("censysio_id")
        api_secret = self.get_key("censysio_secret")
        c = CensysHosts(api_id, api_secret)
        for email in emails:
            email = email.strip('"')
            self.heading(email, level=0)
            try:
                report = c.aggregate(
                    f'services.tls.certificates.leaf_data.subject.email_address:"{email}"',
                    field="services.tls.certificates.leaf_data.names",
                    num_buckets=self.options.get("num_buckets", 100),
                )
            except CensysException:
                self.print_exception()
                continue
            for bucket in report.get("buckets", []):
                domain = bucket.get("key")
                self.insert_domains(domain=domain, notes=f"Email: {email}")
