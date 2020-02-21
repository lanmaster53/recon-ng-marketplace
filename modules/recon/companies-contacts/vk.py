from recon.core.module import BaseModule
from recon.mixins.oauth import ExplicitOauthMixin

class Module(BaseModule, ExplicitOauthMixin):

    meta = {
        'Name': 'vk.com Profile and Contact Harvester',
        'Author': 'Andrey Zhukov from USSC',
        'Description': "Harvests profiles from vkontakte. Updates the 'contacts' and 'profiles' tables",
        'required_keys': ['vkontakte_api', 'vkontakte_secret'],
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL'
    }


    def get_vkontakte_access_token(self):
        return self.get_explicit_oauth_token(
            'vkontakte',
            'friends',
            'https://oauth.vk.com/authorize',
            'https://oauth.vk.com/access_token'
        )

    def module_run(self, companies):
        #self.delete_key('vkontakte_token')
        access_token = self.get_vkontakte_access_token()
        if not access_token:
            return

        for company in companies:
            self.heading(company, level=0)
            self.get_groups(company, access_token)

    def get_groups(self, company, token):
        url = 'https://api.vk.com/method/groups.search'
        resp = self.request('GET', url, params={'q': company, 'access_token': token, 'count': 1000, 'v': 5.103})
        for group in resp.json()['response']['items']:
            if type(group) is not int:
                self.output( "%s (%s) - %s" % ( group['name'], group['screen_name'], 'closed' if group['is_closed'] == 1 else 'open' ) )
                self.get_contacts(group['id'], token)

    def get_contacts(self, group_id, token):
        url = 'https://api.vk.com/method/users.search'
        offset = 0
        while True:
            resp = self.request('GET', url, params={'group_id': group_id, 'access_token': token, 'fields': 'contacts,screen_name', 'count': 10, 'offset': offset, 'v': 5.103})
            if not resp.json()['response']['items']:
                break
            for user in resp.json()['response']['items']:
                if type(user) is not int:
                    offset += 1
                    first_name = user['first_name']
                    last_name = user['last_name']
                    uid = user['id']
                    username = user['screen_name']
                    self.insert_contacts( first_name=first_name, last_name=last_name )
                    if "id%d"%uid != username:
                        self.insert_profiles( username=username, resource='vk', url='https://vk.com/' + username, category='social', notes="%s %s" % (first_name, last_name) )
