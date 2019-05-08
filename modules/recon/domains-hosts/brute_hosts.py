from recon.core.module import BaseModule
from recon.mixins.resolver import ResolverMixin
from recon.mixins.threads import ThreadingMixin
import dns.resolver
import os

class Module(BaseModule, ResolverMixin, ThreadingMixin):

    meta = {
        'name': 'DNS Hostname Brute Forcer',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Brute forces host names using DNS. Updates the \'hosts\' table with the results.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': (
            ('wordlist', os.path.join(BaseModule.data_path, 'hostnames.txt'), True, 'path to hostname wordlist'),
        ),
        'files': (
            'hostnames.txt',
        ),
    }

    def module_run(self, domains):
        with open(self.options['wordlist']) as fp:
            words = fp.read().split()
        resolver = self.get_resolver()
        for domain in domains:
            self.heading(domain, level=0)
            wildcard = None
            try:
                answers = resolver.query(f"*.{domain}")
                wildcard = answers.response.answer[0][0]
                self.output(f"Wildcard DNS entry found for '{domain}' at '{wildcard}'.")
            except (dns.resolver.NoNameservers, dns.resolver.Timeout):
                self.error('Invalid nameserver.')
                continue
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                self.verbose('No Wildcard DNS entry found.')
            self.thread(words, domain, resolver, wildcard)

    def module_thread(self, word, domain, resolver, wildcard):
        max_attempts = 3
        attempt = 0
        while attempt < max_attempts:
            host = f"{word}.{domain}"
            try:
                answers = resolver.query(host)
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                self.verbose(f"{host} => No record found.")
            except dns.resolver.Timeout:
                self.verbose(f"{host} => Request timed out.")
                attempt += 1
                continue
            else:
                # process answers
                if answers.response.answer[0][0] == wildcard:
                    self.verbose(f"{host} => Response matches the wildcard.")
                else:
                    for answer in answers.response.answer:
                        for rdata in answer:
                            if rdata.rdtype in (1, 5):
                                if rdata.rdtype == 1:
                                    address = rdata.address
                                    self.alert(f"{host} => (A) {address}")
                                    self.insert_hosts(host, address)
                                if rdata.rdtype == 5:
                                    cname = rdata.target.to_text()[:-1]
                                    self.alert(f"{host} => (CNAME) {cname}")
                                    self.insert_hosts(cname)
                                    # add the host in case a CNAME exists without an A record
                                    self.insert_hosts(host)
            # break out of the loop
            attempt = max_attempts
