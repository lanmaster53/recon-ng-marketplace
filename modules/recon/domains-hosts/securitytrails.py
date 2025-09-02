from recon.core.module import BaseModule

class Module(BaseModule):
    meta = {
        'name': 'SecurityTrails',
        'author': 'Jan-Jaap Korpershoek (@jjk96)',
        'version': '1.0',
        "required_keys": ["securitytrails_api"],
        'description': 'Uses the SecurityTrails API to find host names. Updates the \'hosts\' table with the results.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        for domain in domains:
            self.heading(domain, level=0)
            url = f'https://api.securitytrails.com/v1/domain/{domain}/subdomains'
            resp = self.request('GET', url, headers={
                "apikey": self.get_key('securitytrails_api')
            })
            if resp.status_code != 200:
                self.error(f"Got unexpected response code: {resp.status_code}")
                continue

            data = resp.json()
            for subdomain in data['subdomains']:
                host = f"{subdomain}.{domain}"
                self.insert_hosts(host=host)
