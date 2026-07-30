from urllib.parse import quote

from recon.core.module import BaseModule
from recon.utils.parsers import parse_name


class Module(BaseModule):

    meta = {
        'name': 'Xquik Profile Contact Harvester',
        'author': 'Burak Bayir (@kriptoburak)',
        'version': '1.0',
        'description': 'Queries Xquik for X profile data and adds names and '
        'locations to the \'contacts\' table.',
        'required_keys': ['xquik_api'],
        'comments': (
            'API documentation: https://docs.xquik.com',
            'Not affiliated with X Corp.',
        ),
        'query': "SELECT DISTINCT username FROM profiles WHERE username IS "
        "NOT NULL AND (resource LIKE 'Twitter' COLLATE NOCASE OR resource "
        "LIKE 'X' COLLATE NOCASE)",
    }

    def module_run(self, usernames):
        api_key = self.keys.get('xquik_api')
        headers = {'x-api-key': api_key}
        for username in usernames:
            handle = username[1:] if username.startswith('@') else username
            url = f"https://xquik.com/api/v1/x/users/{quote(handle, safe='')}"
            resp = self.request('GET', url, headers=headers)
            if resp.status_code == 404:
                self.output(f"X profile not found: {handle}")
                continue
            if resp.status_code == 401:
                self.error('Xquik API key rejected. Check xquik_api.')
                continue
            if resp.status_code == 402:
                self.error('Xquik subscription required. Subscribe first.')
                continue
            if resp.status_code == 429:
                self.error('Xquik rate limit reached. Try again later.')
                continue
            if resp.status_code != 200:
                self.error(f"Unexpected Xquik response: {resp.status_code}")
                continue
            try:
                data = resp.json()
            except ValueError:
                self.error('Invalid Xquik response. Try again.')
                continue
            if not isinstance(data, dict):
                self.error('Invalid Xquik response. Try again.')
                continue
            name = data.get('name') or ''
            fname, mname, lname = parse_name(name)
            region = data.get('location') or None
            if any((fname, lname)):
                self.insert_contacts(
                    first_name=fname,
                    middle_name=mname,
                    last_name=lname,
                    title='X Profile',
                    region=region,
                )
