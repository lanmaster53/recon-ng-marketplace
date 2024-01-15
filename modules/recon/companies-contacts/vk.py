from recon.core.module import BaseModule
from recon.mixins.oauth import ExplicitOauthMixin
from time import sleep

API_LEVEL = '5.103'


class Module(BaseModule, ExplicitOauthMixin):

    meta = {
        'name': 'Vkontakte profiles and contacts harvester',
        'author': 'Andrey Zhukov from USSC',
        'version': '1.0',
        'description': "Harvests profiles from vkontakte. Updates the 'contacts' and 'profiles' tables.",
        'required_keys': ['vkontakte_api', 'vkontakte_secret'],
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
        'options': (
            ('interval', 1, True, 'interval in seconds between api requests'),
        ),
    }

    def get_vkontakte_access_token(self):
        return self.get_explicit_oauth_token(
            'vkontakte',
            'friends',
            'https://oauth.vk.com/authorize',
            'https://oauth.vk.com/access_token'
        )

    def check_access_token(self, token):
        url = 'https://api.vk.com/method/account.getInfo'
        resp = self.request('GET', url, params={'access_token': token, 'v': API_LEVEL})
        # Check if access_token has expired
        if 'error' in resp.json() and resp.json()['error']['error_code'] == 5:
            return False
        else:
            return True

    def module_run(self, companies):
        access_token = self.get_vkontakte_access_token()
        if not access_token:
            return
        # Updating access_token
        if not self.check_access_token(access_token):
            self.remove_key('vkontakte_token')
            access_token = self.get_vkontakte_access_token()

        for company in companies:
            self.heading(company, level=0)
            self.get_groups(company, access_token)

    def get_groups(self, company, token):
        url = 'https://api.vk.com/method/groups.search'
        resp = self.request('GET', url, params={'q': company, 'access_token': token, 'count': 1000, 'v': API_LEVEL})
        if 'error' in resp.json():
            self.error(str(resp.json()['error']))
            return
        for group in resp.json()['response']['items']:
            if type(group) is not int:
                self.output("%s (%s) - %s" % (group['name'], group['screen_name'], 'closed' if group['is_closed'] == 1 else 'open'))
                self.get_contacts(group['id'], token)

    def get_contacts(self, group_id, token):
        url = 'https://api.vk.com/method/users.search'
        offset = 0
        while True:
            resp = self.request('GET', url, params={'group_id': group_id, 'access_token': token, 'fields': 'contacts,screen_name', 'count': 10, 'offset': offset, 'v': API_LEVEL})
            sleep(self.options['interval'])
            if 'error' in resp.json():
                self.error(str(resp.json()['error']))
                continue
            if not resp.json()['response']['items']:
                break
            for user in resp.json()['response']['items']:
                if type(user) is not int:
                    offset += 1
                    first_name = user['first_name']
                    last_name = user['last_name']
                    uid = user['id']
                    username = user['screen_name']
                    self.insert_contacts(first_name=first_name, last_name=last_name)
                    if "id%d" % uid != username:
                        self.insert_profiles(username=username, resource='vk', url='https://vk.com/' + username, category='social', notes="%s %s" % (first_name, last_name))
