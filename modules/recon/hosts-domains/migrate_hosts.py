from recon.core.module import BaseModule
import os
import re

class Module(BaseModule):

    meta = {
        'name': 'Hosts to Domains Data Migrator',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.1',
        'description': 'Adds a new domain for all the hostnames stored in the \'hosts\' table.',
        'comments': (
            'This modules considers that everything after the first element could contain other hosts besides the current. Therefore, hosts > 2 domains deep will create domains > 2 elements in length.',
        ),
        'query': 'SELECT DISTINCT host FROM hosts WHERE host IS NOT NULL',
        'files': ['suffixes.txt'],
    }

    def module_run(self, hosts):
        # ip address regex
        regex = r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'
        # only migrate hosts that aren't ip addresses
        hosts = [x for x in hosts if not re.match(regex, x[0])]
        with open(os.path.join(self.data_path, 'suffixes.txt')) as f:
            suffixes = [line.strip().lower() for line in f if len(line)>0 and line[0] != '#']
        domains = self.hosts_to_domains(hosts, suffixes)
        for domain in domains:
            self.insert_domains(domain=domain)
