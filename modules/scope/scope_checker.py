from recon.core.module import BaseModule
import ipaddress


class Module(BaseModule):
    meta = {
        'name': 'Scope Checker',
        'author': 'Ryan Hays',
        'version': '1.0',
        'description': 'Compares the hosts table and removes hosts that are not found within the provided scope document. '
                       'Scope should be defined within the document either by single IP or in CIDR notation (eg. 192.168.1.0/24)',
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
        'options': (
            ('filename', None, True, 'path and filename for scope document'),
        ),
    }

    def module_run(self, hosts):
        cidr_dict = {}
        with open(self.options['filename'], 'rt') as fp:
            for cidr in fp:
                try:
                    cidr_dict[ipaddress.ip_network(cidr.rstrip())] = cidr.rstrip()
                except ValueError:
                    self.error(f"Invalid CIDR notation for: {cidr.rstrip()}")

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

        self.output(f"Remove {cnt} out of scope hosts from the hosts table.")
