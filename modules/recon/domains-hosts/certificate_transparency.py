from recon.core.module import BaseModule


class Module(BaseModule):

    meta = {
        'name': 'Certificate Transparency Search (crt.sh)',
        'author': 'Rich Warren (richard.warren@nccgroup.trust); revisions by Nicholas Curran',
        'version': '1.4',
        'description': (
            'Searches certificate transparency data via crt.sh, adding newly '
            'identified hosts to the hosts table. SAN entries are filtered '
            'against the queried domain so unrelated tenants from '
            'multi-tenant certificates are not ingested.'
        ),
        'comments': (
            'A longer global TIMEOUT setting may be required for large domains.',
            'crt.sh historically has availability issues — 5xx and timeout '
            'responses are surfaced loudly so partial enumeration is visible. '
            'Run certspotter as a redundant CT source when reliability matters.',
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        source_disabled = False
        for domain in domains:
            self.heading(domain, level=0)
            if source_disabled:
                self.verbose(
                    f"Skipping '{domain}': crt.sh disabled earlier this run."
                )
                continue
            url = f"https://crt.sh/?q=%25.{domain}&output=json"

            try:
                resp = self.request(
                    'GET', url,
                    headers={'Accept': 'application/json'},
                )
            except Exception as exc:
                # Once crt.sh starts timing out / refusing connections, every
                # remaining query in this run will hit the same wall. Stop now.
                source_disabled = True
                self._loud_upstream_failure(
                    domain,
                    f"request failed ({exc.__class__.__name__}: {exc}); "
                    f"disabling crt.sh for the rest of this run"
                )
                continue

            if resp.status_code in (429, 502, 503, 504):
                retry_after = (resp.headers or {}).get('Retry-After')
                detail = f" (Retry-After: {retry_after}s)" if retry_after else ''
                source_disabled = True
                self._loud_upstream_failure(
                    domain,
                    f"crt.sh returned HTTP {resp.status_code}{detail}; "
                    f"the service is frequently overloaded. Disabling for "
                    f"the rest of this run; use certspotter or "
                    f"subdomain_center as alternatives"
                )
                continue

            if resp.status_code != 200:
                self.error(
                    f"Invalid response for '{domain}': HTTP {resp.status_code}"
                )
                continue

            try:
                certs = resp.json()
            except ValueError:
                self.error(
                    f"Non-JSON response for '{domain}' "
                    f"(likely an HTML error page)."
                )
                continue

            for cert in certs:
                name_value = cert.get('name_value') or ''
                # crt.sh separates SANs with newlines; split() handles whitespace.
                for raw in name_value.split():
                    entry = raw.lower().rstrip('.')
                    if '@' in entry:
                        email = entry
                        host = entry.split('@', 1)[1]
                    else:
                        email = None
                        host = entry
                    # Skip wildcard SANs — not real hosts; the apex they cover
                    # is already in the domains table.
                    if host.startswith('*.'):
                        continue
                    # Multi-tenant certs (Adobe Scene7, Cloudflare Universal SSL,
                    # etc.) list many unrelated SANs alongside ours. Drop
                    # anything that isn't this domain or a subdomain.
                    if not _matches_domain(host, domain):
                        continue
                    if email is not None:
                        self.insert_contacts(email=email)
                    self.insert_hosts(host=host)

    def _loud_upstream_failure(self, domain, detail):
        """Emit on BOTH alert() and error() channels so a long pipeline run
        can't bury an upstream outage. INCOMPLETE is grep-friendly."""
        msg = (
            f"UPSTREAM ERROR: crt.sh enumeration for '{domain}' "
            f"is INCOMPLETE — {detail}."
        )
        self.alert(msg)
        self.error(msg)


def _matches_domain(host, domain):
    """True iff host is `domain` or a subdomain of `domain` (case-insensitive)."""
    if not host:
        return False
    h = host.lower().rstrip('.')
    d = domain.lower().rstrip('.')
    return h == d or h.endswith('.' + d)
