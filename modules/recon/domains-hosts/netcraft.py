from recon.core.module import BaseModule
from http.cookiejar import CookieJar
from urllib.parse import unquote_plus, urlencode
import re
import hashlib
import time
import random

class Module(BaseModule):

    meta = {
        'name': 'Netcraft Hostname Enumerator',
        'author': 'thrapt (thrapt@gmail.com)',
        'version': '1.1',
        'description': 'Harvests hosts from Netcraft.com. Updates the \'hosts\' table with the results.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        url = 'http://searchdns.netcraft.com/'
        pattern = r'<a class="results-table__host" href="http://(.*?)/"'
        # answer challenge cookie
        cookiejar = CookieJar()
        payload = {'restriction': 'site+ends+with', 'host': 'test.com'}
        resp = self.request('GET', url, params=payload, cookies=cookiejar)
        cookiejar = resp.cookies
        for cookie in cookiejar:
            if cookie.name == 'netcraft_js_verification_challenge':
                challenge = cookie.value
                response = hashlib.sha1(unquote_plus(challenge).encode('utf-8')).hexdigest()
                cookiejar.set_cookie(self.make_cookie('netcraft_js_verification_response', f"{response}", '.netcraft.com'))
                break
        for domain in domains:
            self.heading(domain, level=0)
            payload['host'] = domain
            subs = []
            # execute search engine queries and scrape results storing subdomains in a list
            # loop until no Next Page is available
            while True:
                self.verbose(f"URL: {url}?{urlencode(payload)}")
                resp = self.request('GET', url, params=payload, cookies=cookiejar)
                content = resp.text
                sites = re.findall(pattern, content)
                # create a unique list
                sites = list(set(sites))
                # add subdomain to list if not already exists
                for site in sites:
                    if site not in subs:
                        subs.append(site)
                        self.insert_hosts(site)
                # verifies if there's more pages to look while grabbing the correct 
                # values for our payload...
                link = re.findall(r'(\blast\=\b|\bfrom\=\b)(.*?)&', content)
                if not link:
                    break
                else:
                    payload['last'] = link[0][1]
                    payload['from'] = link[1][1]
                    self.verbose('Next page available! Requesting again...' )
                    # sleep script to avoid lock-out
                    self.verbose('Sleeping to Avoid Lock-out...')
                    time.sleep(random.randint(5,15))
            if not subs:
                self.output('No results found.')
