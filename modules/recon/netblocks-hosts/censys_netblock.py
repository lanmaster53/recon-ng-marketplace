from recon.core.module import BaseModule

from censys.ipv4 import CensysIPv4
from censys.base import CensysException

class Module(BaseModule):
    meta = {
        'name': 'Censys hosts by netblock',
        'author': 'J Nazario',
        'version': 1.0,
        'description': 'Harvests hosts and ports from the Censys API by using the \'ip\' search operator. Updates the \'hosts\' and the \'ports\' tables with the results.',
        'query': 'SELECT DISTINCT netblock FROM netblocks WHERE netblock IS NOT NULL',
        'required_keys': ['censysio_id', 'censysio_secret'],
    }

    def module_run(self, netblocks):
        api_id = self.get_key('censysio_id')
        api_secret = self.get_key('censysio_secret')
        c = CensysIPv4(api_id, api_secret)
        IPV4_FIELDS = [ 'ip', 'protocols', 'location.country', 
                        'location.latitude', 'location.longitude']          
        for netblock in netblocks:
            self.heading(netblock, level=0)
            try:
                payload = c.search('ip:{0}'.format(netblock), IPV4_FIELDS)
            except CensysException:
                continue
            for result in payload:
                self.insert_hosts(ip_address=result['ip'], 
                               country=result.get('location.country', ''),
                               latitude=result.get('location.latitude', ''), 
                               longitude=result.get('location.longitude', ''))
                for protocol in result['protocols']:
                    port, service = protocol.split('/')
                    self.insert_ports(ip_address=result['ip'], port=port, protocol=service)
