from recon.core.module import BaseModule
from itertools import groupby
from lxml.html import fromstring
from http.cookiejar import CookieJar
import json
import os
from urllib.parse import urlparse, parse_qs

def _optionize(s):
    return 'ghdb_%s' % (s.replace(' ', '_').lower())

def _build_options(ghdb):
    categories = []
    for key, group in groupby([x['category'] for x in sorted(ghdb, key=lambda x: x['category'])]):
        categories.append((_optionize(key), False, True, 'enable/disable the %d dorks in this category' % (len(list(group)))))
    return categories

class DuckDuckGoWebMixin(object):
    cookiejar = CookieJar()
    user_agent = 'curl/7.50.1'

    def search_ddg_web(self, query, limit=0, start_page=1):
        url = 'https://duckduckgo.com/lite/'
        num = 100
        page = start_page
        set_page = lambda x: ( (x - 1) * num ) + 1
        query = self._search_operators_google_to_ddg(query)
        params = { 'q': query }
        domain = [ word for word in query.split() if word.find('site:') != -1 ][0][5:]
        results = []
        self.verbose('Searching DuckDuckGo for: %s' % (query))
        while True:
            resp = self.request('POST', url, params=params, cookiejar=self.cookiejar, redirect=False, agent=self.user_agent)
            # handle error conditions
            if resp.status_code != 200:
                self.error('DuckDuckGo encountered an unknown error.')
                break
            tree = fromstring(resp.text)
            links = tree.xpath('//table[3]//a/@href')
            regmatch = re.compile('^/l/.*uddg=([^/&]+).*')
            for link in links:
                matches = regmatch.match(link)
                if matches != None:
                    uri = matches.group(1)
                    self.output(uri)
                    if urlparse.urlparse(uri).netloc.find(domain) != -1:
                        results.append( urllib.unquote_plus( uri ) )
            if limit == page:
                break
            break
        return results

    def _search_operators_google_to_ddg(self, query):
        return query\
        .replace('allintext:', 'inbody:')\
        .replace('allintitle:', 'intitle:')\
        .replace('intext:', 'inbody:')\
        .replace('ext:', 'filetype(not working):')\
        .replace('allinurl:', '???:')\
        .replace('inurl:', '???:')

class Module(BaseModule, DuckDuckGoWebMixin):

    with open(os.path.join(BaseModule.data_path, 'ghdb.json')) as fp:
        ghdb = json.load(fp)

    meta = {
        'name': 'Google Hacking Database / DuckDuckGo',
        'Author': 'Andrey Zhukov from USSC',
        'description': 'Searches for possible vulnerabilites in a domain by leveraging the Google Hacking Database (GHDB) and the \'site\' search operator. Updates the \'vulnerabilities\' table with the results.',
        'comments': (
            'Special thanks to the Offenvise Security crew for maintaining the GHDB and making it available to open source projects like Recon-ng. Thanks Muts!',
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': [
            ('dorks', None, False, 'file containing an alternate list of Google dorks'),
        ] + _build_options(ghdb),
    }

    def module_run(self, domains):
        dorks = self.ghdb
        # use alternate list of dorks if the option is set
        if self.options['dorks'] and os.path.exists(self.options['dorks']):
            with open(self.options['dorks']) as fp:
                dorks = [x.strip() for x in fp.readlines()]
        for domain in domains:
            self.heading(domain, level=0)
            base_query = 'site:%s' % (domain)
            for dork in dorks:
                # build query based on alternate list
                if isinstance(dork, str):
                    query = ' '.join((base_query, dork))
                    self._search(query)
                # build query based on ghdb entry
                elif isinstance(dork, dict):
                    if not dork['querystring']:
                        continue
                    if self.options[_optionize(dork['category'])]:
                        # parse the query string to extract the dork syntax
                        parsed = urlparse.urlparse(dork['querystring'])
                        params = urlparse.parse_qs(parsed.query)
                        # unparsable url
                        if 'q' not in params:
                            continue
                        query = ' '.join((base_query, params['q'][0]))
                        self._search(query)

    def _search(self, query):
        for result in self.search_ddg_web(query):
            host = urlparse.urlparse(result).netloc
            data = {
                'host': host,
                'reference': query,
                'example': result,
                'category': 'Google Dork',
            }
            self.insert_vulnerabilities(**data)
