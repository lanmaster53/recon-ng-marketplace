from recon.core.module import BaseModule
from urllib.parse import urlparse


class Module(BaseModule):

    meta = {
        'name': 'AlienVault OTX Subdomain Enumerator',
        'author': 'Nicholas Curran (@ncurran)',
        'version': '1.0',
        'description': (
            'Queries the AlienVault OTX url_list endpoint for each domain and '
            'extracts unique subdomains. No API key required. Paginates '
            'automatically until OTX signals no more pages or the max_pages '
            'option is reached.'
        ),
        'comments': (
            'Free, no API key required — OTX url_list is a public endpoint.',
            'Uses the "hostname" field on each url_list entry; falls back to '
            'urllib.parse on the "url" field if hostname is missing.',
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': (
            ('per_page', 500, True, 'results per OTX page (max 500)'),
            ('max_pages', 100, True, 'safety cap on pages fetched per domain'),
        ),
    }

    API_URL = 'https://otx.alienvault.com/api/v1/indicators/domain/{domain}/url_list'

    def module_run(self, domains):
        per_page = self.options['per_page']
        max_pages = self.options['max_pages']

        for domain in domains:
            domain = domain.lower()
            self.heading(domain, level=0)

            hosts = set()
            pages_fetched = 0

            for page in range(1, max_pages + 1):
                resp = self.request(
                    'GET',
                    self.API_URL.format(domain=domain),
                    params={'page': page, 'limit': per_page},
                )
                pages_fetched = page

                if resp.status_code != 200:
                    self.error(f"Unexpected response ({resp.status_code}) on page {page} for '{domain}'.")
                    break

                data = resp.json() or {}
                for entry in data.get('url_list') or []:
                    host = self._extract_host(entry)
                    if host and (host == domain or host.endswith(f'.{domain}')):
                        hosts.add(host)

                if not data.get('has_next'):
                    break

            for host in sorted(hosts):
                self.insert_hosts(host=host)
            self.output(
                f"{len(hosts)} unique subdomain(s) for '{domain}' "
                f"(fetched {pages_fetched} page(s))."
            )

    @staticmethod
    def _extract_host(entry):
        host = (entry.get('hostname') or '').lower().strip()
        if host:
            return host
        url = entry.get('url') or ''
        if url:
            return (urlparse(url).hostname or '').lower().strip()
        return ''
