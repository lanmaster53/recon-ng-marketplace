from recon.core.module import BaseModule


class Module(BaseModule):

    meta = {
        'name': 'Alienvault',
        'author': 'Jan-Jaap Korpershoek (@JJK96)',
        'version': '1.0',
        'description': 'Searches AlienVault for subdomains',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        for domain in domains:
            self.heading(domain, level=0)
            resp = self.request(
                'GET',
                f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns",
                headers={"Accept": "application/json"},
            )
            
            if resp.status_code != 200:
                self.output(f"Invalid response for '{domain}'")
                continue
            
            for result in resp.json()['passive_dns']:
                host = result['hostname']
                self.insert_hosts(host)
