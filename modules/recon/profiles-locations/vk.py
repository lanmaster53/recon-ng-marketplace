from recon.core.module import BaseModule
from recon.mixins.oauth import ExplicitOauthMixin
from datetime import datetime
from time import sleep

API_LEVEL = '5.103'


class Module(BaseModule, ExplicitOauthMixin):

    meta = {
        'name': 'Vkontakte locations enumerator',
        'author': 'Andrey Zhukov from USSC',
        'version': '1.0',
        'description': 'Get all possible locations of users media.',
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

    def get_photos(self, user_id, album_id, access_token):
        url = 'https://api.vk.com/method/photos.get'
        resp = self.request('GET', url, params={'owner_id': user_id, 'album_id': album_id, 'access_token': access_token, 'v': API_LEVEL})
        sleep(self.options['interval'])
        if 'error' in resp.json():
            self.error(str(resp.json()['error']))
            return
        if not resp.json()['response']['items']:
            return
        for photo in resp.json()['response']['items']:
            yield photo

    def get_albums(self, user_id, access_token):
        url = 'https://api.vk.com/method/photos.getAlbums'
        resp = self.request('GET', url, params={'owner_id': user_id, 'access_token': access_token, 'v': API_LEVEL})
        sleep(self.options['interval'])
        if 'error' in resp.json():
            self.error(str(resp.json()['error']))
            return
        if not resp.json()['response']['items']:
            return
        for album in resp.json()['response']['items']:
            album_id = album['id']
            yield album_id

    def get_users_id(self, usernames, access_token):
        url = 'https://api.vk.com/method/users.get'
        for offset in range(0, len(usernames), 10):
            resp = self.request('GET', url, params={'user_ids': ','.join(usernames[offset:offset+10]), 'access_token': access_token, 'v': API_LEVEL})
            sleep(self.options['interval'])
            if 'error' in resp.json():
                self.error(str(resp.json()['error']))
                return
            for user in resp.json()['response']:
                yield user['id']

    def module_run(self, usernames):
        access_token = self.get_vkontakte_access_token()
        if not access_token:
            return
        # Updating access_token
        if not self.check_access_token(access_token):
            self.remove_key('vkontakte_token')
            access_token = self.get_vkontakte_access_token()

        for user_id in self.get_users_id(usernames, access_token):
            self.output('user_id: %d' % user_id)
            for album_id in self.get_albums(user_id, access_token):
                self.output('album: %s' % album_id)
                for pushpin in self.get_photos(user_id, album_id, access_token):
                    if 'lat' in pushpin.keys() and 'long' in pushpin.keys():
                        source = "vk"
                        screen_name = pushpin.get('id')
                        profile_name = pushpin.get('owner_id')
                        profile_url = "https://vk.com/id%d" % profile_name if profile_name > 0 else "https://vk.com/public%d" % abs(profile_name)
                        max_size = 0
                        for image in pushpin["sizes"]:
                            if image.get("width") * image.get("height") > max_size:
                                media_url = image.get("url")
                        thumb_url = pushpin.get('src') or ''
                        message = pushpin.get('text') or ''
                        latitude = pushpin.get('lat') or ''
                        longitude = pushpin.get('long') or ''
                        time = datetime.fromtimestamp(pushpin.get('created') or 0)
                        self.insert_pushpins(source, '', '', profile_url, media_url, thumb_url, message, latitude, longitude, time)
