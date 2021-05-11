from recon.core.module import BaseModule

from censys.search import CensysIPv4
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        'name': 'Censys hosts by hostname',
        'author': 'Censys Team',
        'version': 2.0,
        'description': 'Retrieves all IPs for a given hostname. '
                       'Updates the "hosts" and "ports" tables.',
        'query': 'SELECT DISTINCT host FROM hosts WHERE host IS NOT NULL',
        'required_keys': ['censysio_id', 'censysio_secret'],
        'dependencies': ['censys>=2.0.0'],
    }

    def module_run(self, hosts):
        api_id = self.get_key('censysio_id')
        api_secret = self.get_key('censysio_secret')
        c = CensysIPv4(api_id, api_secret)
        IPV4_FIELDS = [
            'ip', 'protocols', 'location.country',
            'location.latitude', 'location.longitude'
        ]
        for host in hosts:
            self.heading(host, level=0)
            try:
                payload = c.search('a:{0}'.format(host), IPV4_FIELDS)
            except CensysException:
                continue
            for result in payload:
                self.insert_hosts(
                    host=host,
                    ip_address=result['ip'],
                    country=result.get('location.country', ''),
                    latitude=result.get('location.latitude', ''),
                    longitude=result.get('location.longitude', ''))
                for protocol in result['protocols']:
                    port, service = protocol.split('/')
                    self.insert_ports(
                        ip_address=result['ip'], port=port, protocol=service)
