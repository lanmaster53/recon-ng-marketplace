import itertools

from recon.core.module import BaseModule

from censys.search import CensysIPv4
from censys.common.exceptions import CensysException


def grouper(n, iterable):
    # via https://stackoverflow.com/a/8991553
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


class Module(BaseModule):
    meta = {
        'name': 'Censys ports by IP',
        'author': 'Censys Team',
        'version': 2.0,
        'description': 'Retrieves the open ports for each IP address. '
                       'Updates the \'ports\' table with the results.',
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
        'required_keys': ['censysio_id', 'censysio_secret'],
        'dependencies': ['censys>=2.0.0'],
    }

    def module_run(self, hosts):
        api_id = self.get_key('censysio_id')
        api_secret = self.get_key('censysio_secret')
        c = CensysIPv4(api_id, api_secret)
        IPV4_FIELDS = ['ip', 'protocols']
        for ips in grouper(20, hosts):
            try:
                results = c.search(' OR '.join(
                    ['ip:{0}'.format(x) for x in ips]), IPV4_FIELDS)
            except CensysException:
                continue
            for result in results:
                ip = result['ip']
                for protocol in result['protocols']:
                    port, service = protocol.split('/')
                    self.insert_ports(
                        ip_address=ip, port=port, protocol=service)
