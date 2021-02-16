from recon.core.module import BaseModule
import ssl
from socket import setdefaulttimeout, timeout
import re
import cryptography.x509


class Module(BaseModule):

    meta = {
        'name': 'SSL Scanner SAN Lookup',
        'author': 'Ryan Hays (@_ryanhays)',
        'version': '1.1',
        'description': 'Queries the ports table to build a list of IP Address:Ports. It then connects to each service '
                       'updating the Ports table with the certificate common name and then adds the Subject Alt Names '
                       'to the hosts table.',
        'query': 'SELECT DISTINCT ("ip_address" || ":" || "port") FROM ports WHERE ip_address IS NOT NULL',
        'dependancies': ['cryptography']
    }

    def module_run(self, hosts):
        # https://stackoverflow.com/a/2894918
        dn_regex_pat = r'^[a-zA-Z\d-]{,63}(\.[a-zA-Z\d-]{,63})*$'
        for host in hosts:
            setdefaulttimeout(10)
            ip, port = host.split(':')
            try:
                cert = ssl.get_server_certificate((ip, port), ssl_version=ssl.PROTOCOL_TLS)
            except (ssl.SSLError, ConnectionResetError, ConnectionRefusedError, ssl.SSLEOFError, OSError):
                self.alert(f"This is not a proper HTTPS service: {ip}:{port}")
                continue
            except timeout:
                self.alert(f"Timed out connecting to host {ip}:{port}")
                continue

            x509_cert = cryptography.x509.load_pem_x509_certificate(cert.encode())
            commonnames = x509_cert.subject.get_attributes_for_oid(cryptography.x509.NameOID.COMMON_NAME)

            for cn in commonnames:
                if re.match(dn_regex_pat, cn.value):
                    self.insert_ports(host=cn.value, ip_address=ip, port=port, protocol='tcp')
                else:
                    self.debug(f"Not a valid Common Name: {cn.value}")

            san_ext = x509_cert.extensions.get_extension_for_oid(cryptography.x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value
            subaltnames = san_ext.get_values_for_type(cryptography.x509.DNSName)

            for san in subaltnames:
                if re.match(dn_regex_pat, san):
                    self.insert_hosts(host=san)
