from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'BinaryEdge.io Ports lookup',
        'author': 'Ryan Hays',
        'version': '1.0',
        'description': 'Uses the BinaryEdge API to discover open services for IP Addresses.',
        'required_keys': ['binaryedge_api'],
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
    }

    def module_run(self, ipaddrs):
        key = self.keys.get('binaryedge_api')
        for ipaddr in ipaddrs:
            self.heading(ipaddr, level=0)
            resp = self.request('GET', f"https://api.binaryedge.io/v2/query/ip/{ipaddr}", headers={'X-Key': key})
            if resp.status_code == 200:
                for event in resp.json().get('events'):
                    for result in event['results']:
                        self.insert_ports(ip_address=ipaddr, port=result['target']['port'],
                                          protocol=result['target']['protocol'])
