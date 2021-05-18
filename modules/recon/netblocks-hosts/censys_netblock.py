from recon.core.module import BaseModule

from censys.search import CensysIPv4
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        'name': 'Censys hosts by netblock',
        'author': 'Censys Team',
        'version': 2.0,
        'description': 'Retrieves hosts and ports for a neyblock. '
                       'Updates the \'hosts\' and the \'ports\' tables with the results.',
        'query': 'SELECT DISTINCT netblock FROM netblocks WHERE netblock IS NOT NULL',
        'required_keys': ['censysio_id', 'censysio_secret'],
        'dependencies': ['censys>=2.0.0'],
    }

    def module_run(self, netblocks):
        api_id = self.get_key('censysio_id')
        api_secret = self.get_key('censysio_secret')
        c = CensysIPv4(api_id, api_secret)
        IPV4_FIELDS = [
            'ip', 'protocols', 'location.country',
            'location.latitude', 'location.longitude'
        ]
        for netblock in netblocks:
            self.heading(netblock, level=0)
            try:
                payload = c.search('ip:{0}'.format(netblock), IPV4_FIELDS)
            except CensysException:
                continue
            for result in payload:
                ip_address = result['ip']
                self.insert_hosts(
                    ip_address=ip_address,
                    country=result.get('location.country'),
                    latitude=result.get('location.latitude'),
                    longitude=result.get('location.longitude'),
                )
                for protocol in result.get('protocols', []):
                    port, service = protocol.split('/')
                    self.insert_ports(
                        ip_address=ip_address, port=port, protocol=service)
