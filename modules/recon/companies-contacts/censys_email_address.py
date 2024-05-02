from recon.core.module import BaseModule

from censys.search import CensysHosts
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        "name": "Censys - Emails by Company",
        "author": "Censys, Inc. <support@censys.io>",
        "version": 2.1,
        "description": (
            "Retrieves email addresses from the TLS certificates for a"
            " company. This module queries the"
            " 'services.tls.certificates.leaf_data.subject.email_address'"
            " field and updates the 'contacts' table with the results."
        ),
        "query": (
            "SELECT DISTINCT company FROM companies WHERE company IS NOT NULL"
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

    def module_run(self, companies):
        api_id = self.get_key("censysio_id")
        api_secret = self.get_key("censysio_secret")
        c = CensysHosts(api_id, api_secret)
        for company in companies:
            company = company.strip('"')
            self.heading(company, level=0)
            try:
                report = c.aggregate(
                    "same_service(services.tls.certificates.leaf_data.subject.email_address:*"
                    " and "
                    f'services.tls.certificates.leaf_data.subject.organization:"{company}")',
                    field="services.tls.certificates.leaf_data.subject.email_address",
                    num_buckets=int(self.options.get("NUM_BUCKETS", "100")),
                )
            except CensysException:
                self.print_exception()
                continue
            for bucket in report.get("buckets", []):
                email = bucket.get("key")
                self.insert_contacts(email=email)
