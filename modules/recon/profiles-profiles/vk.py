from recon.core.module import BaseModule
from recon.mixins.oauth import ExplicitOauthMixin
from datetime import datetime

class Module(BaseModule, ExplicitOauthMixin):

    meta = {
        'Name': 'Vkontakte Profile Enumerator',
        'Author': 'Andrey Zhukov from USSC',
        'Description': 'Get usernames by user_ids',
        'required_keys': ['vkontakte_api', 'vkontakte_secret'],
        'query': "SELECT DISTINCT username FROM profiles WHERE username IS NOT NULL AND resource LIKE 'VK' COLLATE NOCASE"
    }

    def get_vkontakte_access_token(self):
        return self.get_explicit_oauth_token(
            'vkontakte',
            'friends',
            'https://oauth.vk.com/authorize',
            'https://oauth.vk.com/access_token'
        )

    def module_run(self, usernames):
        access_token = self.get_vkontakte_access_token()
        if not access_token:
            return

        url = 'https://api.vk.com/method/users.get'
        for offset in range(0, len(usernames), 10):
            resp = self.request('GET', url, params={'user_ids': ','.join(usernames[offset:offset+10]), 'fields': 'screen_name', 'access_token': access_token, 'v': 5.103})
            if resp.json().get('response'):
                for user in resp.json()['response']:
                    if user.get('screen_name'):
                        username = user['screen_name']
                        name = "%s %s" % ( user.get('first_name'), user.get('last_name') )
                        self.insert_profiles(username=username, resource='vk', url='https://vk.com/' + username, category='social', notes=name)
