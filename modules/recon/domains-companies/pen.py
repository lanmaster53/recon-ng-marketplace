from recon.core.module import BaseModule
import re

class Module(BaseModule):

    meta = {
        'name': 'IANA Private Enterprise Number Company-by-Domain Lookup',
        'author': 'Jonathan M. Wilbur <jonathan@wilbur.space>',
        'version': '1.1',
        'description': 'Given a domain, finds companies in the IANA Private Enterprise Number (PEN) registry and adds them to the \'companies\' table.',
        'required_keys': [],
        'comments': (),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': (),
    }

    def module_run(self, domains):
        url = 'https://www.iana.org/assignments/enterprise-numbers/enterprise-numbers'
        resp = self.request('GET', url)
        if resp.status_code != 200:
            self.alert('When retrieving IANA PEN Registry, got HTTP status code ' + str(resp.status_code) + '!')
        for domain in domains:
            dom = re.escape(domain)
            regex = r'(\d+)\s*\n\s{2}(.*)\s*\n\s{4}(.*)\s*\n\s{6}(.*)' + dom + r'\s*\n'
            matchfound = False
            for match in re.finditer(regex, resp.text, re.IGNORECASE):
                company = match.groups()[1]
                self.insert_companies(company)
                matchfound = True
            if not matchfound:
                self.alert('No matches found for domain \'' + domain + '\'')
