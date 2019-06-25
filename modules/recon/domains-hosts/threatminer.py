from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'ThreatMiner DNS lookup',
        'author': 'Pedro Rodrigues',
        'version': '1.0',
        'description': 'Use ThreatMiner API to discover subdomains.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        for domain in domains:
            self.heading(domain, level=0)
            resp = self.request('GET', f"https://api.threatminer.org/v2/domain.php?rt=5&q={domain}")
            if resp.json().get('status_code') == '200':
                for subdomain in resp.json().get('results'):
                    self.insert_hosts(host=subdomain)
