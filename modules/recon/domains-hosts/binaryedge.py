from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'BinaryEdge.io DNS lookup',
        'author': 'Ryan Hays',
        'version': '1.0',
        'description': 'Uses the BinaryEdge API to discover subdomains.',
        'required_keys': ['binaryedge_api'],
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        key = self.get_key('binaryedge_api')
        for domain in domains:
            self.heading(domain, level=0)
            resp = self.request(url=f"https://api.binaryedge.io/v2/query/domains/dns/{domain}", headers={'X-Key': key})
            if resp.status_code == 200:
                for subdomain in resp.json().get('events'):
                    if "A" in subdomain:
                        self.insert_hosts(host=subdomain['domain'], ip_address=subdomain['A'][0])
                    else:
                        self.insert_hosts(host=subdomain['domain'])
