from recon.core.module import BaseModule
from recon.mixins.threads import ThreadingMixin


class Module(BaseModule, ThreadingMixin):

    meta = {
        'name': 'NameChk.com Username Validator',
        'author': 'Tim Tomes (@lanmaster53), thrapt (thrapt@gmail.com) and Ryan Hays (@_ryanhays)',
        'version': '1.0',
        'description': 'Leverages NameChk.com API to validate the existance of usernames on specific web sites and '
                       'updates the \'profiles\' table with the results.',
        'required_keys': ['namechk_api'],
        'query': 'SELECT DISTINCT username FROM profiles WHERE username IS NOT NULL',
    }

    def module_run(self, usernames):
        key = self.keys.get('namechk_api')
        headers = {'authorization': f"Bearer {key}", 'Accept': 'application/vnd.api.v1+json'}
        # Gets a list of available services
        avail_sites = self.request('GET', 'https://api.namechk.com/services/available.json', headers=headers)
        if avail_sites.status_code == 200:
            for username in usernames:
                self.heading(username, level=0)
                self.thread(avail_sites.json(), username, headers)

    def module_thread(self, site, username, headers):
        payload = {'site': site['short_name'], 'username': username}
        resp = self.request('POST', 'https://api.namechk.com/services/check.json', data=payload, headers=headers)
        if resp.status_code == 200:
            if not resp.json().get('available'):
                self.insert_profiles(username=username, resource=site['name'], url=resp.json().get('callback_url'),
                                     category=site['category'])
                self.query('DELETE FROM profiles WHERE username = ? and url IS NULL', (username,))
