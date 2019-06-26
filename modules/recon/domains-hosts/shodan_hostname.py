from recon.core.module import BaseModule
from recon.mixins.search import ShodanAPIMixin
import re


class Module(BaseModule, ShodanAPIMixin):

    meta = {
        'name': 'Shodan Hostname Enumerator',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Harvests hosts from the Shodan API by using the \'hostname\' search operator. Updates the \'hosts\' table with the results.',
        'required_keys': ['shodan_api'],
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': (
            ('limit', 1, True, 'limit number of api requests per input source (0 = unlimited)'),
        ),
    }

    def module_run(self, domains):
        limit = self.options['limit']
        for domain in domains:
            self.heading(domain, level=0)
            query = f"hostname:{domain}"
            results = self.search_shodan_api(query, limit)
            for host in results:
                address = host['ip_str']
                port = host['port']
                if not host['hostnames']:
                    host['hostnames'] = [None]
                for hostname in host['hostnames']:
                    self.insert_ports(ip_address=address, port=port, host=hostname)
                    self.insert_hosts(host=hostname, ip_address=address)
