from recon.core.module import BaseModule


class Module(BaseModule):

    meta = {
        'name': 'Certspotter Certificate Transparency',
        'author': 'Nicholas Curran',
        'version': '1.1',
        'description': (
            'Searches certificate transparency data via the SSLMate Certspotter '
            'API, adding newly identified hosts to the hosts table. '
            'Paginates automatically until all issuances are retrieved.'
        ),
        'comments': (
            'No API key required (free tier: 10 include_subdomains queries/hour).',
            'Set the certspotter_api key to increase rate limits.',
            'SAN entries from multi-tenant certificates (e.g. Adobe Scene7, '
            'Cloudflare Universal SSL) are filtered against the queried domain '
            'so unrelated tenants are not ingested.',
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        source_disabled = False
        for domain in domains:
            self.heading(domain, level=0)
            if source_disabled:
                self.verbose(
                    f"Skipping '{domain}': certspotter disabled earlier this run."
                )
                continue
            after = None
            while True:
                params = {
                    'domain': domain,
                    'include_subdomains': 'true',
                    'expand': 'dns_names',
                }
                if after:
                    params['after'] = after

                resp = self.request(
                    'GET',
                    'https://api.certspotter.com/v1/issuances',
                    params=params,
                )

                if resp.status_code == 429:
                    # Free-tier Certspotter is 10 include_subdomains queries/hour;
                    # once we've hit the limit, every remaining domain in this
                    # run is going to 429 too, so disable the source for the
                    # rest of the run instead of thrashing.
                    retry_after = (resp.headers or {}).get('Retry-After')
                    detail = f" (Retry-After: {retry_after}s)" if retry_after else ''
                    msg = (
                        f"RATE LIMITED: certspotter free tier exhausted on "
                        f"'{domain}'{detail}. Enumeration for this domain is "
                        f"INCOMPLETE — set 'certspotter_api' key to raise the "
                        f"limit, or re-run after the quota resets. Disabling "
                        f"certspotter for the rest of this run."
                    )
                    self.alert(msg)
                    self.error(msg)
                    source_disabled = True
                    break
                if resp.status_code != 200:
                    self.error(f"Unexpected response for '{domain}': {resp.status_code}")
                    break

                certs = resp.json()
                if not certs:
                    break

                for cert in certs:
                    for raw in cert.get('dns_names') or []:
                        entry = raw.lower().rstrip('.')
                        if '@' in entry:
                            email = entry
                            host = entry.split('@', 1)[1]
                        else:
                            email = None
                            host = entry
                        # Skip wildcard SANs — they aren't real hosts and the
                        # apex they cover will already be in the domains table.
                        if host.startswith('*.'):
                            continue
                        # Multi-tenant certs (Adobe Scene7, Cloudflare Universal
                        # SSL, etc.) list many unrelated SANs alongside ours.
                        # Drop anything that isn't this domain or a subdomain.
                        if not _matches_domain(host, domain):
                            continue
                        if email is not None:
                            self.insert_contacts(email=email)
                        self.insert_hosts(host=host)

                after = certs[-1]['id']


def _matches_domain(host, domain):
    """True iff host is `domain` or a subdomain of `domain` (case-insensitive)."""
    if not host:
        return False
    h = host.lower().rstrip('.')
    d = domain.lower().rstrip('.')
    return h == d or h.endswith('.' + d)
