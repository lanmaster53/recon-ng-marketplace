from recon.core.module import BaseModule
import json

class Module(BaseModule):

    meta = {
        'name': 'BinaryEdge.io Ports lookup',
        'author': 'Ryan Hays',
        'version': '1.1',
        'description': 'Uses the BinaryEdge API to discover open services for IP Addresses.',
        'required_keys': ['binaryedge_api'],
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
    }

    def module_run(self, ipaddrs):
        key = self.keys.get('binaryedge_api')
        for ipaddr in ipaddrs:
            self.heading(ipaddr, level=0)
            resp = self.request('GET', f"https://api.binaryedge.io/v1/query/latest/{ipaddr}", headers={'X-Token': key})
            if resp.status_code == 200:
                rawData = resp.content.decode('utf-8')
                rawData = rawData.replace('\r', '').replace('\n', '').replace('}{', '},{')
                clean = '[' + rawData + ']'
                pdata = json.loads(clean)
                for item in pdata:
                  self.insert_ports(ip_address=ipaddr, port=item['target']['port'], protocol=['target']['protocol'])
