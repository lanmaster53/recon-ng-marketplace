from recon.core.module import BaseModule
import shodan
import time


class Module(BaseModule):

    meta = {
        'name': 'Shodan IP Enumerator',
        'author': 'Tim Tomes (@lanmaster53) and Matt Puckett (@t3lc0) & Ryan Hays (@_ryanhays)',
        'version': '1.2',
        'description': 'Harvests port information from the Shodan API by using the \'ip\' search operator. Updates the '
                       '\'ports\' table with the results.',
        'required_keys': ['shodan_api'],
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
        'options': (
            ('limit', 1, True, 'limit number of api requests per input source (0 = unlimited)'),
        ),
        'dependencies': ['shodan']
    }

    def module_run(self, ipaddrs):
        limit = self.options['limit']
        api = shodan.Shodan(self.keys.get('shodan_api'))
        for ipaddr in ipaddrs:
            self.heading(ipaddr, level=0)
            try:
                ipinfo = api.host(ipaddr)
                for port in ipinfo['data']:
                    try:
                        for hostname in port['hostnames']:
                            self.insert_ports(host=hostname, ip_address=ipaddr, port=port['port'],
                                              protocol=port['transport'])
                    except KeyError:
                        self.insert_ports(ip_address=ipaddr, port=port['port'], protocol=port['transport'])
            except shodan.exception.APIError:
                pass

            time.sleep(limit)
