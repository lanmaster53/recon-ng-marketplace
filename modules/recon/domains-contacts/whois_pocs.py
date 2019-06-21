from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'Whois POC Harvester',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Uses the ARIN Whois RWS to harvest POC data from whois queries for the given domain. Updates the \'contacts\' table with the results.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        headers = {'Accept': 'application/json'}
        for domain in domains:
            self.heading(domain, level=0)
            url = f"http://whois.arin.net/rest/pocs;domain={domain}"
            self.verbose(f"URL: {url}")
            resp = self.request('GET', url, headers=headers)
            if 'Your search did not yield any results.' in resp.text:
                self.output('No contacts found.')
                continue
            handles = [x['@handle'] for x in resp.json()['pocs']['pocRef']] if type(resp.json()['pocs']['pocRef']) == list else [resp.json()['pocs']['pocRef']['@handle']]
            for handle in handles:
                url = f"http://whois.arin.net/rest/poc/{handle}"
                self.verbose(f"URL: {url}")
                resp = self.request('GET', url, headers=headers)
                poc = resp.json()['poc']
                emails = poc['emails']['email'] if type(poc['emails']['email']) == list else [poc['emails']['email']]
                for email in emails:
                    fname = poc['firstName']['$'] if 'firstName' in poc else None
                    lname = poc['lastName']['$']
                    name = ' '.join([x for x in [fname, lname] if x])
                    email = email['$']
                    title = 'Whois contact'
                    city = poc['city']['$'].title()
                    state = poc['iso3166-2']['$'].upper() if 'iso3166-2' in poc else None
                    region = ', '.join([x for x in [city, state] if x])
                    country = poc['iso3166-1']['name']['$'].title()
                    if email.lower().endswith(domain.lower()):
                        self.insert_contacts(first_name=fname, last_name=lname, email=email, title=title, region=region, country=country)
