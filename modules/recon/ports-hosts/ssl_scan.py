from recon.core.module import BaseModule
import ssl
from socket import setdefaulttimeout, timeout
import M2Crypto
import re


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
        cn_regex_pat = r'.*CN=(.+?)(,|$)'
        dn_regex_pat = r'^(?!:\/\/)([a-zA-Z0-9-_]+\.)*[a-zA-Z0-9][a-zA-Z0-9-_]+\.[a-zA-Z]{2,11}?$'
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

            x509 = M2Crypto.X509.load_cert_string(cert)
            regex = re.compile(cn_regex_pat)
            commonname = regex.search(x509.get_subject().as_text()).group(1)

            if re.match(dn_regex_pat, commonname):
                self.output(f"Updating ports table for {ip} to include host {commonname}")
                self.query('UPDATE ports SET ip_address=?, host=?, port=?, protocol=? WHERE ip_address=?',
                           (ip, commonname, port, 'tcp', ip))
            else:
                self.alert(f"Not a valid Common Name: {commonname}")

            try:
                subaltname = x509.get_ext('subjectAltName').get_value().split(',')
            except LookupError:
                continue

            for san in subaltname:
                san = san.split(':')[1]
                if re.match(dn_regex_pat, san):
                    self.insert_hosts(host=san)
