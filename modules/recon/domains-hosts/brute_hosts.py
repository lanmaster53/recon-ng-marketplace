from recon.core.module import BaseModule
from recon.mixins.resolver import ResolverMixin
from recon.mixins.threads import ThreadingMixin
import dns.resolver
import os
import random
import string

# How many random non-existent labels to resolve when establishing a zone's
# wildcard baseline. >1 catches round-robin / GeoDNS wildcards that rotate
# IPs — a single-probe baseline only ever sees one member of the rotation,
# so real hosts that happen to land on a *different* rotation member than
# the one probe caught slip through as false "real" hosts (KNOWN_ISSUES.md
# 2026-06-22 robinhood.com: 5,692 of the 4-IP wildcard's hosts leaked through
# this exact gap). Mirrors permute.py's WILDCARD_PROBES.
WILDCARD_PROBES = 3

class Module(BaseModule, ResolverMixin, ThreadingMixin):

    meta = {
        'name': 'DNS Hostname Brute Forcer',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.2',
        'description': (
            'Brute forces host names using DNS. Updates the \'hosts\' table with the results. '
            'Wildcard-DNS aware: probes the zone\'s wildcard multiple times to catch a full '
            f'round-robin/GeoDNS IP set ({WILDCARD_PROBES} probes, not just one), and drops any '
            'candidate whose A-record set is a subset of that baseline. Records provenance chain '
            'on each insert (e.g. "alienvault.brute_hosts") so it is traceable how each '
            'discovered host arrived.'
        ),
        # Multi-column query: opt into provenance tracking. Each input row
        # arrives as a (domain, parent_module, parent_provenance) tuple.
        'query': 'SELECT DISTINCT domain, module, provenance FROM domains WHERE domain IS NOT NULL',
        'accepts_provenance': True,
        'options': (
            ('wordlist', os.path.join(BaseModule.data_path, 'hostnames.txt'), True, 'path to hostname wordlist'),
        ),
        'files': ['hostnames.txt'],
    }

    def module_run(self, domains):
        with open(self.options['wordlist']) as fp:
            words = fp.read().split()
        resolver = self.get_resolver()
        for domain_row in domains:
            domain, parent_chain = _unpack_provenance_row(domain_row)
            self.heading(domain, level=0)
            wildcard_ips = self._wildcard_baseline(resolver, domain)
            if wildcard_ips:
                self.output(
                    f"Wildcard DNS on '{domain}' — baseline {sorted(wildcard_ips)} "
                    f"({WILDCARD_PROBES}-probe sample); candidates matching only this "
                    f"set are dropped."
                )
            new_chain = f"{parent_chain}.brute_hosts" if parent_chain else 'brute_hosts'
            self.thread(words, domain, resolver, wildcard_ips, new_chain)

    def _wildcard_baseline(self, resolver, domain):
        """Return the frozenset of A IPs that *.<domain> serves, sampled over
        WILDCARD_PROBES random non-existent labels — catches round-robin/
        GeoDNS wildcards that rotate across more than one IP. Empty frozenset
        means no wildcard (each probe NXDOMAIN'd)."""
        ips = set()
        for _ in range(WILDCARD_PROBES):
            label = 'wc' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
            try:
                answers = resolver.query(f'{label}.{domain}')
                for answer in answers.response.answer:
                    for rdata in answer:
                        if rdata.rdtype == 1:  # A
                            ips.add(rdata.address)
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                pass
            except (dns.resolver.NoNameservers, dns.resolver.Timeout):
                pass
        return frozenset(ips)

    def module_thread(self, word, domain, resolver, wildcard_ips, provenance):
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
                a_ips = {rdata.address for answer in answers.response.answer
                         for rdata in answer if rdata.rdtype == 1}
                if wildcard_ips and a_ips and a_ips <= wildcard_ips:
                    self.verbose(f"{host} => {sorted(a_ips)} (wildcard catch, dropped).")
                else:
                    for answer in answers.response.answer:
                        for rdata in answer:
                            if rdata.rdtype in (1, 5):
                                if rdata.rdtype == 1:
                                    address = rdata.address
                                    self.alert(f"{host} => (A) {address}")
                                    self.insert_hosts(host=host, ip_address=address,
                                                      provenance=provenance)
                                if rdata.rdtype == 5:
                                    cname = rdata.target.to_text()[:-1]
                                    self.alert(f"{host} => (CNAME) {cname}")
                                    self.insert_hosts(host=cname, provenance=provenance)
                                    # add the host in case a CNAME exists without an A record
                                    self.insert_hosts(host=host, provenance=provenance)
            # break out of the loop
            attempt = max_attempts


def _unpack_provenance_row(row):
    """Normalise an input row that may be a bare string or a
    (value, parent_module, parent_provenance) tuple. Returns
    (value, parent_chain) where parent_chain is the parent's provenance
    if present, else its module, else an empty string. Mirrors permute's
    helper — both pilot modules use the same shape."""
    if isinstance(row, (tuple, list)):
        value = row[0] if len(row) > 0 else ''
        parent_module = row[1] if len(row) > 1 else None
        parent_provenance = row[2] if len(row) > 2 else None
        return value, (parent_provenance or parent_module or '')
    return row, ''
