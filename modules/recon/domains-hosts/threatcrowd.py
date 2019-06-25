from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'ThreatCrowd DNS lookup',
        'author': 'mike2dot0',
        'version': '1.0',
        'description': 'Leverages the ThreatCrowd passive DNS API to discover hosts/subdomains.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        for domain in domains:
            self.heading(domain, level=0)
            resp = self.request('GET', f"https://www.threatcrowd.org/searchApi/v2/domain/report/?domain={domain}")
            if resp.json().get('response_code') == '1':
                for subdomain in resp.json().get('subdomains'):
                    self.insert_hosts(host=subdomain)
