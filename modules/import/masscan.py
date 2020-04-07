from recon.core.module import BaseModule
from xml.etree import ElementTree


class Module(BaseModule):
    meta = {
        'name': 'Masscan XML Output Importer',
        'author': 'Ryan Hays (@_ryanhays)',
        'version': '1.0',
        'description': 'Imports hosts and ports into the respective databases from Masscan XML output.',
        'options': (
            ('filename', None, True, 'path and filename for list input'),
        ),
    }

    def module_run(self):
        with open(self.options['filename'], 'rt') as f:
            tree = ElementTree.parse(f)

        for host in tree.findall('host'):
            address = host.find('address')
            if address.attrib.get('addrtype') == 'ipv4':
                ipaddress = address.attrib.get('addr')
                self.insert_hosts(ip_address=ipaddress)

            for host_port in host.find('ports').findall('port'):
                if host_port.find('state').get('state') != 'open':
                    continue

                self.insert_ports(ip_address=ipaddress, port=host_port.attrib.get('portid'),
                                  protocol=host_port.attrib.get('protocol'))
