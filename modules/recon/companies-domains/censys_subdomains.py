from recon.core.module import BaseModule

from censys.search import CensysCertificates
from censys.common.exceptions import CensysException


class Module(BaseModule):
    meta = {
        'name': 'Censys subdomains by company',
        'author': 'Censys Team',
        'version': 2.0,
        'description': 'Retrieves subdomains for a company. '
                       'Updates the \'domains\' tables with the results.',
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
        'required_keys': ['censysio_id', 'censysio_secret'],
        'dependencies': ['censys>=2.0.0'],
    }

    def module_run(self, companies):
        api_id = self.get_key('censysio_id')
        api_secret = self.get_key('censysio_secret')
        c = CensysCertificates(api_id, api_secret)
        SEARCH_FIELDS = [
            'parsed.subject.organization',
            'parsed.subject.organizational_unit'
        ]
        for company in companies:
            self.heading(company, level=0)
            try:
                query = ' OR '.join(
                    ['{0}:"{1}"'.format(x, company) for x in SEARCH_FIELDS])
                payload = c.search(query, ['parsed.names'])
            except CensysException:
                continue
            for result in payload:
                for name in result.get('parsed.names', []):
                    if name.startswith('*.'):
                        self.insert_domains(name.replace('*.', ''))
