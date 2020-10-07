from recon.core.module import BaseModule
from xml.etree import ElementTree


class Module(BaseModule):
    meta = {
        'name': 'Nmap XML Output Importer',
        'author': 'Ryan Hays (@_ryanhays)',
        'version': '1.1',
        'description': 'Imports hosts and ports into the respective databases from Nmap XML output.',
        'options': (
            ('filename', None, True, 'path and filename for list input'),
        ),
    }

    def module_run(self):
        with open(self.options['filename'], 'rt') as f:
            tree = ElementTree.parse(f)

        for host in tree.findall('host'):
            for ip in host.findall('address'):
                ipaddress = ip.attrib.get('addr')
                try:
                    for hostname in host.find('hostnames').findall('hostname'):
                        self.insert_domains(domain=hostname.attrib.get('name'))
                        self.insert_hosts(host=hostname.attrib.get('name'), ip_address=ipaddress)
                except AttributeError:
                    self.insert_hosts(ip_address=ipaddress)

            try:
                for host_port in host.find('ports').findall('port'):
                    if host_port.find('state').get('state') != 'open':
                        continue
                    port = host_port.attrib.get('portid')
                    protocol = host_port.attrib.get('protocol')
                    self.insert_ports(ip_address=ipaddress, port=port, protocol=protocol)
            except AttributeError:
                pass
