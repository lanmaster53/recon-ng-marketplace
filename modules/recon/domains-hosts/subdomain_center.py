from recon.core.module import BaseModule


# Status codes that signal the source is broken for the duration of this run
# (rate limit hit, origin overloaded, etc.) — the per-source fail-fast trigger.
# When any of these come back, we abandon this source for remaining domains
# rather than burning wall-clock retrying the same upstream issue.
_FAIL_FAST_STATUS = {429, 502, 503, 504, 521, 522, 523, 524}


class Module(BaseModule):

    meta = {
        'name': 'Subdomain Center',
        'author': 'Nicholas Curran (@ncurran)',
        'version': '1.0',
        'description': (
            'Passive subdomain enumeration via the public subdomain.center API. '
            'Different failure mode than crt.sh / certspotter — useful as a '
            'redundant CT-adjacent source when stacking free providers.'
        ),
        'comments': (
            'No API key required.',
            'On the first 429 / 5xx / Cloudflare-origin-unreachable response '
            '(521-524) the module disables itself for the rest of this run '
            'rather than thrashing per-domain — alerted loudly so partial '
            'enumeration is visible.',
            'SAN entries are filtered against the queried domain to avoid '
            'ingesting unrelated tenants from any shared-cert leakage upstream.',
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        source_disabled = False
        for domain in domains:
            self.heading(domain, level=0)

            if source_disabled:
                self.verbose(
                    f"Skipping '{domain}': subdomain.center disabled earlier "
                    f"this run."
                )
                continue

            url = f"https://api.subdomain.center/?domain={domain}"
            try:
                resp = self.request(
                    'GET', url,
                    headers={'Accept': 'application/json'},
                )
            except Exception as exc:
                source_disabled = True
                self._loud_failure(
                    domain,
                    f"request failed ({exc.__class__.__name__}: {exc}); "
                    f"disabling subdomain.center for the rest of this run"
                )
                continue

            if resp.status_code in _FAIL_FAST_STATUS:
                retry_after = (resp.headers or {}).get('Retry-After')
                detail = f" (Retry-After: {retry_after}s)" if retry_after else ''
                source_disabled = True
                self._loud_failure(
                    domain,
                    f"subdomain.center returned HTTP {resp.status_code}{detail}; "
                    f"disabling for the rest of this run"
                )
                continue

            if resp.status_code != 200:
                self.error(
                    f"Invalid response for '{domain}': HTTP {resp.status_code}"
                )
                continue

            try:
                payload = resp.json()
            except ValueError:
                self.error(
                    f"Non-JSON response for '{domain}' (likely an HTML error page)."
                )
                continue

            if not isinstance(payload, list):
                self.error(
                    f"Unexpected response shape for '{domain}': "
                    f"expected list, got {type(payload).__name__}"
                )
                continue

            inserted = 0
            for raw in payload:
                if not isinstance(raw, str):
                    continue
                host = raw.lower().rstrip('.')
                if host.startswith('*.'):
                    continue
                if not _matches_domain(host, domain):
                    continue
                self.insert_hosts(host=host)
                inserted += 1
            self.output(f"{inserted} host(s) from subdomain.center for '{domain}'.")

    def _loud_failure(self, domain, detail):
        msg = (
            f"UPSTREAM ERROR: subdomain.center enumeration starting at "
            f"'{domain}' is INCOMPLETE — {detail}."
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
