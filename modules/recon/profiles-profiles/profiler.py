from recon.core.module import BaseModule
from recon.mixins.threads import ThreadingMixin
from urllib.parse import quote_plus

class Module(BaseModule, ThreadingMixin):

    meta = {
        'name': 'OSINT HUMINT Profile Collector',
        'author': 'Micah Hoffman (@WebBreacher)',
        'version': '1.0',
        'description': 'Takes each username from the profiles table and searches a variety of web sites for those users. The list of valid sites comes from the parent project at https://github.com/WebBreacher/WhatsMyName',
        'comments': (
            'Note: The global timeout option may need to be increased to support slower sites.',
            'Warning: Using this module behind a filtering proxy may cause false negatives as some of these sites may be blocked.',
        ),
        'query': 'SELECT DISTINCT username FROM profiles WHERE username IS NOT NULL',
    }

    def module_run(self, usernames):
        # retrieve list of sites
        url = 'https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json'
        self.verbose(f"Retrieving {url}...")
        resp = self.request('GET', url)
        for user in usernames: 
            self.heading(f"Looking up data for: {user}")
            self.thread(resp.json()['sites'], user)

    def module_thread(self, site, user):
        d = dict(site)
        if d['valid'] == True:
            self.verbose(f"Checking: {d['name']}")
            url = d['uri_check'].replace('{account}', quote_plus(user))
            resp = self.request('GET', url, allow_redirects=False)  
            if resp.status_code == int(d['e_code']):
                self.debug(f"Codes matched {resp.status_code} {d['e_code']}")
                if d['e_string'] in resp.text or d['e_string'] in resp.headers:
                    self.insert_profiles(username=user, url=url, resource=d['name'], category=d['cat'])
                    self.query('DELETE FROM profiles WHERE username = ? and url IS NULL', (user,))
