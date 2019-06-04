from recon.core.module import BaseModule
import ssl
import M2Crypto


class Module(BaseModule):

    meta = {
        'name': 'SSL Scanner SAN Lookup',
        'author': 'Ryan Hays (@_ryanhays)',
        'version': '1.0',
        'description': 'Connects to a Host and pulls the Subject Alternative Names from the IP Address and Port combination.',
        'query': 'SELECT DISTINCT ("ip_address" || ":" || "port") FROM ports WHERE ip_address IS NOT NULL',
    }

    def module_run(self, hosts):
        for host in hosts:
            url, port = host.split(':')
            try:
                cert = ssl.get_server_certificate((url, port))
            except ssl.SSLError:
                self.alert(f"This is not a proper HTTPS service: {host}:{port}")
                continue

            x509 = M2Crypto.X509.load_cert_string(cert)
            x509.get_ext('subjectAltName').get_value()

            for san in x509.get_ext('subjectAltName').get_value().split(','):
                self.insert_ports(ip_address=url, port=port, host=san.split(':')[1], protocol='tcp')
