from recon.core.module import BaseModule
import ssl
import M2Crypto


class Module(BaseModule):

    meta = {
        'name': 'SSL Scanner SAN Lookup',
        'author': 'Ryan Hays (@_ryanhays)',
        'version': '1.0',
        'description': 'Queries the ports table to build a list of IP Address:Ports. It then connects to each service '
                       'updating the Ports table with the certificate common name and then adds the Subject Alt Names '
                       'to the hosts table.',
        'query': 'SELECT DISTINCT ("ip_address" || ":" || "port") FROM ports WHERE ip_address IS NOT NULL',
    }

    def module_run(self, hosts):
        for host in hosts:
            ip, port = host.split(':')
            try:
                cert = ssl.get_server_certificate((ip, port))
            except ssl.SSLError:
                self.alert(f"This is not a proper HTTPS service: {ip}:{port}")
                continue

            x509 = M2Crypto.X509.load_cert_string(cert)
            commonname = x509.get_subject().as_text().split('=')[-1]

            self.output(f"Updating ports table for {ip} to include host {commonname}")
            self.query('UPDATE ports SET ip_address=?, host=?, port=?, protocol=? WHERE ip_address=?',
                       (ip, commonname, port, 'tcp', ip))

            for san in x509.get_ext('subjectAltName').get_value().split(','):
                self.insert_hosts(host=san.split(':')[1])
