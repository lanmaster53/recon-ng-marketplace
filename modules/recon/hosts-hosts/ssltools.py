from recon.core.module import BaseModule
from datetime import datetime
import re

class Module(BaseModule):

    meta = {
        'name': 'SSLTools.com Host Name Lookups',
        'author': 'Tim Maletic (borrowing from the ssl_san module by Zach Graces)',
        'version': '1.0',
        'description': 'Uses the ssltools.com site to obtain host names from a site\'s SSL certificate metadata to update the \'hosts\' table.  Security issues with the certificate trust are pushed to the \'vulnerabilities\' table.',
        'comments': (
            'This module only stores hosts whose domain matches an entry in the domains table.',
        ),
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
        'options': (
            ('restrict', True, True, 'restrict added hosts to current domains'),
        ),
    }

    def module_run(self, hosts):
        # build a regex that matches any of the stored domains
        domains = [x[0] for x in self.query('SELECT DISTINCT domain from domains WHERE domain IS NOT NULL')]
        domains_str = '|'.join([r'\.'+re.escape(x)+'$' for x in domains])
        regex = f"(?:{domains_str})"
        for ip_address in hosts:
            self.heading(ip_address, level=0)
            url = f"http://www.ssltools.com/certificate_lookup/{ip_address}"
            html = self.request('GET', url).text

            # names
            san = re.search('<br>Subject Alternative Names :(.*?)<br>', html)
            cn = re.search('<br>Common Name :(.*?)<br>', html)
            names = ""
            if san is None:
                self.output(f"No Subject Alternative Names found for '{ip_address}'")
            else:
                self.output(f"Subject Alternative Names: '{san.group(1)}'")
                names = san.group(1)
            if cn is None:
                self.output(f"No Common Name found for '{ip_address}'")
            else:
                self.output(f"Common Name: '{cn.group(1)}'")
                names += cn.group(1)
            if not names:
                continue
            hosts = [x.strip() for x in names.split(',') if '*' not in x]
            for host in hosts:
                # apply restriction
                if self.options['restrict'] and not re.search(regex, host):
                    continue
                self.insert_hosts(host)

            # vulns
            data = {}
            data['host'] = ip_address
            data['reference'] = url
            data['status'] = 'unfixed'
            data['publish_date'] = datetime.strptime(re.search(r'<h4>generated at (.*) -\d{4} \(click', html).group(1), '%Y-%m-%d %H:%M:%S')
            vuln_expired = re.search('<br>Incorrect : Certificate date is invalid[^<]*expired[^<]*<br>', html)
            if vuln_expired:
                self.output('Vulnerability: ')
                data['category'] = 'SSL Certificate Expired'
                self.insert_vulnerabilities(**data)
            vuln_hostname_mismatch = re.search('<br>Incorrect : Certificate Name does not match hostname', html)
            if vuln_hostname_mismatch:
                self.output('Vulnerability: ')
                data['category'] = 'SSL Certificate Name Does Not Match Hostname'
                self.insert_vulnerabilities(**data)
            vuln_untrusted = re.search('<br>SSL Certificate is not trusted<br>The certificate is not signed by a trusted authority', html)
            # ssltools appears to say "the certificate is not signed by a trusted authority" whenever there is a trust problem, no matter what the cause
            if vuln_untrusted:
                self.output('Vulnerability: ')
                data['category'] = 'SSL Certificate Not Signed By Trusted Authority'
                self.insert_vulnerabilities(**data)
