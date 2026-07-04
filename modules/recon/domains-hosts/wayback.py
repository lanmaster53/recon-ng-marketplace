from recon.core.module import BaseModule
import re


class Module(BaseModule):

    meta = {
        'name': 'Wayback Machine Subdomain Enumerator',
        'author': 'Nicholas Curran (@ncurran)',
        'version': '1.0',
        'description': (
            'Queries the Wayback Machine CDX API for all archived URLs under each '
            'domain and inserts discovered subdomains into the hosts table.'
        ),
        'comments': (
            'Free, no API key required.',
            'Uses CDX collapse=urlkey to deduplicate results efficiently.',
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        for domain in domains:
            self.heading(domain, level=0)

            params = {
                'url': f'*.{domain}',
                'output': 'text',
                'fl': 'original',
                'collapse': 'urlkey',
                'limit': '100000',
            }

            resp = self.request('GET', 'https://web.archive.org/cdx/search/cdx', params=params)

            if resp.status_code != 200:
                self.error(f"Unexpected response ({resp.status_code}) for '{domain}'.")
                continue

            if not resp.text.strip():
                self.output(f"No archived URLs found for '{domain}'.")
                continue

            hosts = set()
            for line in resp.text.strip().splitlines():
                url = line.strip()
                if not url:
                    continue
                m = re.match(r'https?://([^/:]+)', url)
                if not m:
                    continue
                host = m.group(1).lower()
                if host.endswith(f'.{domain}') or host == domain:
                    hosts.add(host)

            for host in sorted(hosts):
                self.insert_hosts(host=host)
            self.output(f"{len(hosts)} unique hosts found for '{domain}'.")
