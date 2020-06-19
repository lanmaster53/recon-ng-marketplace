from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'BinaryEdge.io DNS lookup',
        'author': 'Ryan Hays',
        'version': '1.2',
        'description': 'Uses the BinaryEdge API to discover subdomains.',
        'required_keys': ['binaryedge_api'],
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        key = self.keys.get('binaryedge_api')
        for domain in domains:
            self.heading(domain, level=0)
            page_num = 1
            domain_count = 0
            total_ans = 1
            while domain_count < total_ans:
                resp = self.request('GET', f"https://api.binaryedge.io/v2/query/domains/dns/{domain}?page={page_num}",
                                    headers={'X-Key': key})
                if resp.status_code == 200:
                    total_ans = resp.json().get('total')

                    for subdomain in resp.json().get('events'):
                        domain_count += 1
                        if "A" in subdomain:
                            self.insert_hosts(host=subdomain['domain'], ip_address=subdomain['A'][0])
                        else:
                            self.insert_hosts(host=subdomain['domain'])
                    page_num += 1
                elif resp.json().get('status') == 400:
                    break
