from recon.core.module import BaseModule

from censys.search import CensysIPv4
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        'name': 'Censys hosts by search terms',
        'author': 'Censys Team',
        'version': 2.0,
        'description': 'Retrieves details for hosts matching an arbitrary Censys query. '
                       'Updates the \'hosts\', \'domains\', and \'ports\' tables with the results.',
        'required_keys': ['censysio_id', 'censysio_secret'],
        'options': (
            ('censys_query', '80.http.get.title: "Welcome to recon-ng"',
             True, 'The Censys query to execute'),
        ),
        'dependencies': ['censys>=2.0.0'],
    }

    def module_run(self):
        api_id = self.get_key('censysio_id')
        api_secret = self.get_key('censysio_secret')
        query = self.options['censys_query']
        c = CensysIPv4(api_id, api_secret)
        IPV4_FIELDS = [
            'ip',
            'protocols',
            'location.country',
            'location.latitude',
            'location.longitude',
            '443.https.tls.certificate.parsed.names',
            '25.smtp.starttls.tls.certificate.parsed.names',
            '110.pop3.starttls.tls.certificate.parsed.names',
        ]
        try:
            payload = list(c.search(query, fields=IPV4_FIELDS))
        except CensysException as e:
            self.error('Error seen: {0}'.format(e))
            return
        if len(payload) < 1:
            self.alert("No results")
            return
        for result in payload:
            names = set()
            for k, v in result.items():
                if k.endswith('.parsed.names'):
                    for name in v:
                        names.add(name)
            if len(names) < 1:
                # make sure we have at least a blank name
                names.add('')
            for name in names:
                if name.startswith('*.'):
                    self.insert_domains(name.replace('*.', ''))
                    continue
                self.insert_hosts(host=name,
                                  ip_address=result['ip'],
                                  country=result.get('location.country', ''),
                                  latitude=result.get('location.latitude', ''),
                                  longitude=result.get('location.longitude', ''))
                for protocol in result['protocols']:
                    port, service = protocol.split('/')
                    self.insert_ports(
                        ip_address=result['ip'], host=name, port=port, protocol=service)
