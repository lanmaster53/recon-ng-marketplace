from recon.core.module import BaseModule

from censys.search import CensysIPv4
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        'name': 'Censys services by company',
        'author': 'Censys Team',
        'version': 2.0,
        'description': 'Retrieves hosts for a company’s ASN. '
                       'Updates the \'hosts\' and the \'ports\' tables with the results.',
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
        'required_keys': ['censysio_id', 'censysio_secret'],
        'dependencies': ['censys>=2.0.0'],
    }

    def module_run(self, companies):
        api_id = self.get_key('censysio_id')
        api_secret = self.get_key('censysio_secret')
        c = CensysIPv4(api_id, api_secret)
        IPV4_FIELDS = [
            'ip', 'protocols',
            '443.https.tls.certificate.parsed.names',
            '25.smtp.starttls.tls.certificate.parsed.names',
            '110.pop3.starttls.tls.certificate.parsed.names',
            'location.country', 'location.latitude',
            'location.longitude'
        ]
        for company in companies:
            self.heading(company, level=0)
            try:
                payload = c.search(
                    'autonomous_system.name:"{0}"'.format(company), IPV4_FIELDS)
            except CensysException:
                continue
            for result in payload:
                names = set(result.get('443.https.tls.certificate.parsed.names', []) +
                            result.get('25.smtp.starttls.tls.certificate.parsed.names', []) +
                            result.get('110.pop3.starttls.tls.certificate.parsed.names', []))
                if len(names) < 1:
                    names.add('')
                for name in names:
                    if name.startswith('*.'):
                        self.insert_domains(domain=name.replace('*.', ''))
                        continue
                    self.insert_hosts(
                        ip_address=result['ip'],
                        host=name,
                        country=result.get('location.country', ''),
                        latitude=result.get('location.latitude', ''),
                        longitude=result.get('location.longitude', ''))
                    for protocol in result['protocols']:
                        port, service = protocol.split('/')
                        self.insert_ports(
                            ip_address=result['ip'], host=name, port=port, protocol=service)
