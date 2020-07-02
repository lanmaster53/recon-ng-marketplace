from recon.core.module import BaseModule
import shodan
import time


class Module(BaseModule):
    meta = {
        'name': 'Shodan IP Enumerator',
        'author': 'Austin Tipton (@hiEntropy404) & Ryan Hays (@_ryanhays)',
        'version': '1.1',
        'description': 'Harvests host and port information from the Shodan API by using the \'org\' search operator. '
                       'Updates the \'hosts\' and \'ports\' tables with the results.',
        'required_keys': ['shodan_api'],
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
        'options': (
            ('limit', 1, True, 'limit number of api requests per input source (0 = unlimited)'),
        ),
        'dependencies': ['shodan']
    }

    def module_run(self, companies):
        limit = self.options['limit']
        api = shodan.Shodan(self.keys.get('shodan_api'))

        for company in companies:
            self.heading(company, level=0)
            query = f"org:\"{company}\""
            try:
                page = 1
                rec_count = 0
                total_results = 1
                while rec_count < total_results:
                    results = api.search(query, page=page)
                    total_results = results['total']
                    for port in results['matches']:
                        rec_count += 1
                        try:
                            for hostname in port['hostnames']:
                                self.insert_ports(host=hostname, ip_address=port['ip_str'], port=port['port'],
                                                  protocol=port['transport'])
                                self.insert_hosts(host=hostname, ip_address=port['ip_str'])
                        except KeyError:
                            self.insert_ports(ip_address=ipaddr, port=port['port'], protocol=port['transport'])

                    page += 1
                    time.sleep(limit)

            except shodan.exception.APIError:
                pass
