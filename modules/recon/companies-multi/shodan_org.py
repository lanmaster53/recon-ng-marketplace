from recon.core.module import BaseModule
from recon.mixins.search import ShodanAPIMixin
import re


class Module(BaseModule, ShodanAPIMixin):

    meta = {
        'name': 'Shodan IP Enumerator',
        'author': 'Austin Tipton (@hiEntropy404)',
        'version': '1.0',
        'description': 'Harvests host and port information from the Shodan API by using the \'org\' search operator. Updates the \'hosts\' and \'ports\' tables with the results.',
        'required_keys': ['shodan_api'],
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
        'options': (
            ('limit', 1, True, 'limit number of api requests per input source (0 = unlimited)'),
        ),
    }

    def module_run(self, companies):
        limit = self.options['limit']
        for company in companies:
            self.heading(company, level=0)
            query = f"org:\"{company}\""
            results = self.search_shodan_api(query, limit)
            for host in results:
                address = host['ip_str']
                port = host['port']
                if not host['hostnames']:
                    host['hostnames'] = [None]
                for hostname in host['hostnames']:
                    self.insert_ports(ip_address=address, port=port, host=hostname)
                    self.insert_hosts(host=hostname, ip_address= address)
