from recon.core.module import BaseModule

from censys.search import CensysHosts
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        "name": "Censys - Companies by Netblock",
        "author": "Censys, Inc. <support@censys.io>",
        "version": 2.1,
        "description": (
            "Retrieves organizations for a company's netblocks. "
            "Updates the 'companies' table with the results."
        ),
        "query": (
            "SELECT DISTINCT netblock FROM netblocks WHERE netblock IS NOT"
            " NULL"
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

    def module_run(self, netblocks):
        api_id = self.get_key("censysio_id")
        api_secret = self.get_key("censysio_secret")
        c = CensysHosts(api_id, api_secret)
        for netblock in netblocks:
            self.heading(netblock, level=0)
            try:
                # we only need one per netblock since they'll all have the same by ASN
                report = c.aggregate(
                    f"ip:{netblock}",
                    fields="autonomous_system.name",
                    num_buckets=int(self.options.get("NUM_BUCKETS", "100")),
                )
            except CensysException:
                self.print_exception()
                continue
            for bucket in report.get("buckets", []):
                company = bucket.get("key")
                self.insert_companies(company=company)
