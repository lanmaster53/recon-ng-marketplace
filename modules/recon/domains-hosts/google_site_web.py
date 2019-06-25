from recon.core.module import BaseModule
from recon.mixins.search import GoogleWebMixin
import re

class Module(BaseModule, GoogleWebMixin):

    meta = {
        'name': 'Google Hostname Enumerator',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Harvests hosts from Google.com by using the \'site\' search operator. Updates the \'hosts\' table with the results.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        for domain in domains:
            self.heading(domain, level=0)
            base_query = 'site:' + domain
            regmatch = re.compile(rf"//([^/]*\.{domain})")
            hosts = []
            # control variables
            new = True
            page = 1
            nr = 100
            # execute search engine queries and scrape results storing subdomains in a list
            # loop until no new subdomains are found
            while new:
                # build query based on results of previous results
                query = ''
                for host in hosts:
                    query += f" -site:{host}"
                # send query to search engine
                results = self.search_google_web(base_query + query, limit=1, start_page=page)
                # extract hosts from search results
                sites = []
                for link in results:
                    site = regmatch.search(link)
                    if site is not None:
                        sites.append(site.group(1))
                # create a unique list
                sites = list(set(sites))
                # add subdomain to list if not already exists
                new = False
                for site in sites:
                    if site not in hosts:
                        hosts.append(site)
                        new = True
                        self.insert_hosts(site)
                if not new:
                    # exit if all subdomains have been found
                    if not results:
                        break
                    else:
                        # intelligently paginate separate from the framework to optimize the number of queries required
                        page += 1
                        self.verbose(f"No New Subdomains Found on the Current Page. Jumping to Result {(page*nr)+1}.")
                        new = True
