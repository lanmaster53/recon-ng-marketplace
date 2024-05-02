from recon.core.module import BaseModule

from censys.search import CensysCertificates
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        "name": "Censys - Subdomains by Company",
        "author": "Censys, Inc. <support@censys.io>",
        "version": 2.1,
        "description": (
            "Retrieves subdomains for a company. This module queries the"
            " 'parsed.subject.organization' field and updates the 'domains'"
            " table with the results."
        ),
        "query": (
            "SELECT DISTINCT company FROM companies WHERE company IS NOT NULL"
        ),
        "options": [
            ("max_records", 100, True, "maximum number of records to retrieve")
        ],
        "required_keys": ["censysio_id", "censysio_secret"],
        "dependencies": ["censys>=2.1.2"],
    }

    def module_run(self, companies):
        api_id = self.get_key("censysio_id")
        api_secret = self.get_key("censysio_secret")
        c = CensysCertificates(api_id, api_secret)
        SEARCH_FIELDS = [
            "parsed.subject.organization",
            "parsed.subject.organizational_unit",
        ]
        for company in companies:
            company = company.strip('"')
            self.heading(company, level=0)
            try:
                query = " OR ".join(
                    ['{0}:"{1}"'.format(x, company) for x in SEARCH_FIELDS]
                )
                res = c.search(
                    query,
                    ["parsed.names"],
                    max_records=self.options.get("max_records", 100),
                )
            except CensysException:
                self.print_exception()
                continue
            domains = set()
            for result in res:
                for name in result.get("parsed.names", []):
                    if name.startswith("*."):
                        name = name.replace("*.", "")
                    domains.add(name)
            for domain in domains:
                self.insert_domains(domain=domain)
