from recon.core.module import BaseModule


class Module(BaseModule):
    meta = {
        'name': 'HackerTarget reverse IP lookup',
        'author': 'Qazeer',
        'version': '1.0',
        'description': 'Uses the HackerTarget.com reverse IP lookup API to find host names associated with IP addresses. Updates the \'hosts\' table with the results.',
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
    }

    def module_run(self, hosts):
        for ip in hosts:
            self.heading(ip, level=0)
            url = 'https://api.hackertarget.com/reverseiplookup/'
            payload = {'q': ip}
            resp = self.request('GET', url, params=payload)
            if resp.status_code != 200:
                self.error(f"Got unexpected response code: {resp.status_code}")
                continue
            if resp.text == '' or 'No DNS A records found' in resp.text:
                self.output('No results found.')
                continue
            if resp.text.startswith('error'):
                self.error(resp.text)
                continue
            if 'API count exceeded' in resp.text:
                self.error(resp.text)
                continue
            for line in resp.text.split("\n"):
                line = line.strip()
                if line == '':
                    continue
                new_host = line.split(",")
                self.insert_hosts(host=new_host, ip_address=ip)
