from recon.core.module import BaseModule
from recon.mixins.threads import ThreadingMixin


class Module(BaseModule, ThreadingMixin):

    meta = {
        'name': 'NameChk.com Username Validator',
        'author': 'Tim Tomes (@LaNMaSteR53) and thrapt (thrapt@gmail.com) and Ryan Hays (@_ryanhays)',
        'version': '1.0',
        'description': 'Leverages NameChk.com API to validate the existance of usernames on specific web sites and '
                       'pdates the \'profiles\' table with the results.',
        'required_keys': ['namechk_api'],
        'comments': (
            'Note: The global timeout option may need to be increased to support slower sites.',
        ),
        'query': 'SELECT DISTINCT username FROM profiles WHERE username IS NOT NULL',
    }

    def module_run(self, usernames):
        key = self.get_key('namechk_api')
        # Gets a list of available services
        avail_sites = self.request(url=f"https://api.namechk.com/services/available.json",
                                   headers={'AUTHORIZATION': f"Bearer {key}", 'Accept': 'application/vnd.api.v1+json'})

        if avail_sites.status_code == 200:
            for username in usernames:
                self.heading(username, level=0)
                self.thread(avail_sites.json(), username, key)

    def module_thread(self, site, username, key):
        resp = self.request(url=f"https://api.namechk.com/services/check.json", method='POST',
                            headers={'AUTHORIZATION': f"Bearer {key}", 'Accept': 'application/vnd.api.v1+json'},
                            payload={'site': site['short_name'], 'username': username})

        if resp.status_code == 200:
            if not resp.json().get('available'):
                self.insert_profiles(username=username, resource=site['name'], url=resp.json().get('callback_url'),
                                     category=site['category'])
                self.query('DELETE FROM profiles WHERE username = ? and url IS NULL', (username,))
