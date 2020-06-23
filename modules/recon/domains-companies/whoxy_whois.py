from recon.core.module import BaseModule


class Module(BaseModule):

    meta = {
        'name': 'Whoxy Whois Lookup',
        'author': 'Ryan Hays (@_ryanhays)',
        'version': '1.1',
        'description': 'Uses the Whoxy API to query whois information for a domain and updates the companies and '
                       'contacts tables. ',
        'required_keys': ['whoxy_api'],
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        key = self.keys.get('whoxy_api')
        for domain in domains:
            self.heading(domain, level=0)
            resp = self.request('GET', f"http://api.whoxy.com/?key={key}&whois={domain}")
            if resp.status_code == 200:
                reg = resp.json().get('registrant_contact')
                adm = resp.json().get('administrative_contact')
                tech = resp.json().get('technical_contact')

                for email in [reg['email_address'], adm['email_address'], tech['email_address']]:
                    self.insert_contacts(email=email)

                for company in [reg['company_name'], adm['company_name'], tech['company_name']]:
                    self.insert_companies(company=company)
