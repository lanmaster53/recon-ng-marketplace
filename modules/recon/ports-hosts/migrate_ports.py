from recon.core.module import BaseModule
import re


class Module(BaseModule):

    meta = {
        'name': 'Ports to Hosts Data Migrator',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Adds a new host for all the hostnames stored in the \'ports\' table.',
    }

    def module_run(self):
        # ip address regex
        regex = r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'
        # get a list of hosts that are not ip addresses
        hosts = [x[0] for x in self.query('SELECT DISTINCT host FROM ports WHERE host IS NOT NULL') if not re.match(regex, x[0])]
        for host in hosts:
            self.insert_hosts(host=host)
