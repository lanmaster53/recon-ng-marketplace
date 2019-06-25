from recon.core.module import BaseModule
from recon.mixins.resolver import ResolverMixin
import dns.resolver
import dns.reversename

class Module(BaseModule, ResolverMixin):

    meta = {
        'name': 'Reverse Resolver',
        'author': 'John Babio (@3vi1john), @vulp1n3, and Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Conducts a reverse lookup for each IP address to resolve the hostname. Updates the \'hosts\' table with the results.',
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
    }

    def module_run(self, addresses):
        max_attempts = 3
        resolver = self.get_resolver()
        for address in addresses:
            attempt = 0
            while attempt < max_attempts:
                try:
                    addr = dns.reversename.from_address(address)
                    hosts = resolver.query(addr, 'PTR')
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    self.verbose(f"{address} => No record found.")
                except dns.resolver.Timeout:
                    self.verbose(f"{address} => Request timed out.")
                    attempt += 1
                    continue
                except dns.resolver.NoNameservers:
                    self.verbose(f"{address} => Invalid nameserver.")
                    #self.error('Invalid nameserver.')
                    #return
                else:
                    for host in hosts:
                        host = str(host)[:-1] # slice the trailing dot
                        self.insert_hosts(host, address)
                # break out of the loop
                attempt = max_attempts
