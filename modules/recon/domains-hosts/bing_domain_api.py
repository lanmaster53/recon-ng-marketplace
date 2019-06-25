from recon.core.module import BaseModule
from recon.mixins.search import BingAPIMixin
from recon.utils.parsers import parse_hostname
import re

class Module(BaseModule, BingAPIMixin):

    meta = {
        'name': 'Bing API Hostname Enumerator',
        'author': 'Marcus Watson (@BranMacMuffin)',
        'version': '1.0',
        'description': 'Leverages the Bing API and "domain:" advanced search operator to harvest hosts. Updates the \'hosts\' table with the results.',
        'required_keys': ['bing_api'],
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': (
            ('limit', 0, True, 'limit total number of api requests (0 = unlimited)'),
        ),
    }

    def module_run(self, domains):
        limit = self.options['limit']
        requests = 0
        for domain in domains:
            self.heading(domain, level=0)
            hosts = []
            results = []
            pages = 1
            base_query = f"domain:{domain}"
            while not limit or requests < limit:
                query = base_query
                # build query string based on api limitations
                for host in hosts:
                    omit_domain = f" -domain:{host}"
                    # https://msdn.microsoft.com/en-us/library/dn760794.aspx
                    if len(query) + len(omit_domain) >= 1500:
                        break
                    query += omit_domain
                # make api requests
                if limit and requests + pages > limit:
                    pages = limit - requests
                last_len = len(results)
                results = self.search_bing_api(query, pages)
                requests += pages
                # iterate through results and add new hosts
                flag = False
                for result in results:
                    host = parse_hostname(result['displayUrl'])
                    if host.endswith('.'+domain) and host not in hosts:
                        hosts.append(host)
                        self.insert_hosts(host)
                        flag = True
                if not flag and last_len == len(results):
                    break
                elif not flag and last_len != len(results):
                    pages += 1
                    self.verbose(f"No new hosts found for the current query. Increasing depth to '{pages}' pages.")
