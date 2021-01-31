from recon.core.module import BaseModule


class Module(BaseModule):

    meta = {
        'name': 'Spyse Subdomain lookup',
        'author': 'Ryan Hays',
        'version': '1.1',
        'description': 'Uses the Spyse API to discover subdomains.',
        'required_keys': ['spyse_api'],
        'options': (
            ('limit', 100, True, 'Limit the number of results returned. Max is 100.'),
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL'
    }

    def module_run(self, domains):
        key = self.keys.get('spyse_api')
        for domain in domains:
            self.heading(domain, level=0)
            offset = 0
            total_ans = 1
            while offset < total_ans:
                resp = self.request('GET', f"https://api.spyse.com/v3/data/domain/subdomain?offset={offset}&"
                                           f"limit={self.options['limit']}&domain={domain}",
                                    headers={"accept": "application/json",
                                             "Authorization": f"Bearer {key}"})

                if resp.status_code == 200:
                    data = resp.json()
                    total_ans = data['data']['max_view_count']

                    for subdomain in data['data']['items']:
                        offset += 1

                        if subdomain['dns_records']['A'] is not None:
                            self.insert_hosts(host=subdomain['name'], ip_address=subdomain['dns_records']['A'][0]['ip'])
                        else:
                            self.insert_hosts(host=subdomain['name'])
                else:
                    break
