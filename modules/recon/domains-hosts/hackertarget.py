from recon.core.module import BaseModule

class Module(BaseModule):
    meta = {
        'name': 'HackerTarget Lookup',
        'author': 'Michael Henriksen (@michenriksen)',
        'version': '1.1',
        'description': 'Uses the HackerTarget.com API to find host names. Updates the \'hosts\' table with the results.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        for domain in domains:
            self.heading(domain, level=0)
            url = 'https://api.hackertarget.com/hostsearch/'
            payload = {'q': domain}
            resp = self.request('GET', url, params=payload)
            if resp.status_code != 200:
                self.error(f"Got unexpected response code: {resp.status_code}")
                continue
            if resp.text == '':
                self.output('No results found.')
                continue
            if resp.text.startswith('error'):
                self.error(resp.text)
                continue
            for line in resp.text.split("\n"):
                line = line.strip()
                if line == '':
                    continue
                host, address = line.split(",")
                self.insert_hosts(host=host, ip_address=address)
