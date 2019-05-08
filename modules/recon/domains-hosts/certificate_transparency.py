from recon.core.module import BaseModule
import json


class Module(BaseModule):

    meta = {
        'name': 'Certificiate Transparency Search',
        'author': 'Rich Warren (richard.warren@nccgroup.trust)',
        'version': '1.0',
        'description': 'Searches certificate transparency data from crt.sh, adding newly identified hosts to the hosts table.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        for domain in domains:
            self.heading(domain, level=0)
            resp = self.request('https://crt.sh/?q=%25.{0}&output=json'.format(domain))
            if resp.status_code != 200:
                self.output('Invalid response for \'%s\'' % domain)
                continue
            for cert in resp.json:
                self.insert_hosts(cert.get('name_value'))
