from recon.core.module import BaseModule
import json


class Module(BaseModule):

    meta = {
        'name': 'Certificiate Transparency Search',
        'author': 'Rich Warren (richard.warren@nccgroup.trust)',
        'version': '1.1',
        'description': 'Searches certificate transparency data from crt.sh, adding newly identified hosts to the hosts '
                       'table.',
        'comments': (
            'A longer global TIMEOUT setting may be required for larger domains.',
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        for domain in domains:
            self.heading(domain, level=0)
            resp = self.request('GET', f"https://crt.sh/?q=%25.{domain}&output=json")
            if resp.status_code != 200:
                self.output(f"Invalid response for '{domain}'")
                continue
            for cert in resp.json():
                name = cert.get('name_value')
                if '@' in name:
                    self.insert_contacts(email=name)
                    self.insert_hosts(name.split('@')[1])
                else:
                    self.insert_hosts(name)
