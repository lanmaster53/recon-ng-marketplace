from recon.core.module import BaseModule
from recon.mixins.oauth import ExplicitOauthMixin
from datetime import datetime
from time import sleep

API_LEVEL = '5.103'


class Module(BaseModule, ExplicitOauthMixin):

    meta = {
        'name': 'Vkontakte profiles enumerator',
        'author': 'Andrey Zhukov from USSC',
        'version': '1.0',
        'description': 'Get usernames by user_ids.',
        'required_keys': ['vkontakte_api', 'vkontakte_secret'],
        'query': "SELECT DISTINCT username FROM profiles WHERE username IS NOT NULL AND resource LIKE 'VK' COLLATE NOCASE",
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

    def module_run(self, usernames):
        access_token = self.get_vkontakte_access_token()
        if not access_token:
            return
        # Updating access_token
        if not self.check_access_token(access_token):
            self.remove_key('vkontakte_token')
            access_token = self.get_vkontakte_access_token()

        url = 'https://api.vk.com/method/users.get'
        for offset in range(0, len(usernames), 10):
            resp = self.request('GET', url, params={'user_ids': ','.join(usernames[offset:offset+10]), 'fields': 'screen_name', 'access_token': access_token, 'v': API_LEVEL})
            sleep(self.options['interval'])
            if 'error' in resp.json():
                self.error(str(resp.json()['error']))
                return
            for user in resp.json()['response']:
                if user.get('screen_name'):
                    username = user['screen_name']
                    name = "%s %s" % (user.get('first_name'), user.get('last_name'))
                    self.insert_profiles(username=username, resource='vk', url='https://vk.com/' + username, category='social', notes=name)
