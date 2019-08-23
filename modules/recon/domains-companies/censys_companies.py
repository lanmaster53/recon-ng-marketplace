from recon.core.module import BaseModule

from censys.ipv4 import CensysIPv4
from censys.base import CensysException

class Module(BaseModule):
    meta = {
        'name': 'Censys companies by domain',
        'author': 'J Nazario',
        'version': 1.0,
        'description': 'Retrieves the TLS certificates for a domain. Updates the \'companies\' table with the values from the subject organization information.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'required_keys': ['censysio_id', 'censysio_secret'],
    }

    def module_run(self, domains):
        api_id = self.get_key('censysio_id')
        api_secret = self.get_key('censysio_secret')
        c = CensysIPv4(api_id, api_secret)
        IPV4_FIELDS = [ '443.https.tls.certificate.parsed.subject.organization',
                        '25.smtp.starttls.tls.certificate.parsed.subject.organization',
                        '465.smtp.tls.tls.certificate.parsed.subject.organization',
                        '587.smtp.starttls.tls.certificate.parsed.subject.organization',
                        '1521.oracle.banner.tls.certificate.parsed.subject.organization',
                        '3306.mysql.banner.tls.certificate.parsed.subject.organizationn',
                        '3389.rdp.banner.tls.certificate.parsed.subject.organization',
                        '5432.postgres.banner.tls.certificate.parsed.subject.organization',
                        '8883.mqtt.banner.tls.certificate.parsed.subject.organization',]
        SEARCH_FIELDS = ['443.https.tls.certificate.parsed.names',
                         '25.smtp.starttls.tls.certificate.parsed.names',
                         '110.pop3.starttls.tls.certificate.parsed.names',]
        for domain in domains:
            self.heading(domain, level=0)
            try:
                query = 'mx:"{0}" OR '.format(domain) + ' OR '.join([ '{0}:"{1}"'.format(x, domain) for x in SEARCH_FIELDS ])
                payload = c.search(query, IPV4_FIELDS) 
            except CensysException:
                continue
            for result in payload:
                orgs = set()
                for k,v in result.items():
                    if k.endswith('.parsed.subject.organization'):
                        for org in v:
                            orgs.add(org)
                for org in orgs:
                    self.insert_companies(company=org)