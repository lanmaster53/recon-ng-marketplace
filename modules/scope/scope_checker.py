from recon.core.module import BaseModule
import ipaddress
import os
import socket


class Module(BaseModule):
    meta = {
        'name': 'Scope Checker',
        'author': 'Ryan Hays',
        'version': '1.0',
        'description': 'Compares the hosts and ports table and removes hosts that are not found within the provided '
                       'scope document. Scope should be defined within the document by one entry per line either by '
                       'single domain, IP, or CIDR notation (eg. google.com, 192.168.1.1, or 192.168.1.0/24)',
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL '
                 'UNION SELECT ip_address FROM ports WHERE ip_address IS NOT NULL',
        'options': (
            ('filename', None, True, 'path and filename for scope document'),
        ),
        'files': (
            'tld_list.txt',
        ),
    }

    def module_run(self, hosts):
        tld_list = []
        with open(os.path.join(self.data_path, 'tld_list.txt'), 'r') as fp:
            for tld in fp:
                if '#' != tld[0]:
                    tld_list.append(tld.rstrip().lower())

        cidr_dict = {}
        with open(self.options['filename'], 'rt') as fp:
            for cidr in fp:
                cidr = cidr.rstrip()

                try:
                    cidr_dict[ipaddress.ip_network(cidr)] = cidr
                except ValueError:
                    if cidr.split('.')[-1].lower() in tld_list:
                        try:
                            ips = socket.gethostbyname_ex(cidr)[2]
                            for ip in ips:
                                cidr_dict[ipaddress.ip_network(ip)] = cidr
                        except socket.gaierror:
                            self.error(f"Couldn't lookup IP Address for: {cidr}")

                    else:
                        self.error(f"Invalid scope item: {cidr}")

        cnt = 0
        for host in hosts:
            in_scope = False
            ip = ipaddress.ip_address(host)
            for net in cidr_dict.keys():
                if ip in net:
                    in_scope = True
                    break

            if not in_scope:
                cnt += 1
                self.alert(f"{str(ip)} not found in scope document removing from hosts table.")
                self.query('DELETE FROM hosts WHERE ip_address=?', (str(ip),))
                self.query('DELETE FROM ports WHERE ip_address=?', (str(ip),))

        self.output(f"Remove {cnt} out of scope hosts.")
