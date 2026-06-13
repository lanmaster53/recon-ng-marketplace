from recon.core.module import BaseModule
from recon.utils.parsers import parse_name
from urllib.parse import quote_plus


class Module(BaseModule):

    meta = {
        'name': 'Xquik Profile Contact Harvester',
        'author': 'Burak Bayir (@kriptoburak)',
        'version': '1.0',
        'description': 'Uses the Xquik API to enrich X/Twitter profiles with '
        'contact data. Updates the \'contacts\' table with the results.',
        'required_keys': ['xquik_api'],
        'query': "SELECT DISTINCT username FROM profiles WHERE username IS "
        "NOT NULL AND (resource LIKE 'Twitter' COLLATE NOCASE OR resource "
        "LIKE 'X' COLLATE NOCASE)",
    }

    def module_run(self, usernames):
        api_key = self.keys.get('xquik_api')
        headers = {'x-api-key': api_key}
        for username in usernames:
            handle = username[1:] if username.startswith('@') else username
            url = f"https://xquik.com/api/v1/x/users/{quote_plus(handle)}"
            resp = self.request('GET', url, headers=headers)
            if resp.status_code == 404:
                self.output(f"X profile not found: {handle}")
                continue
            if resp.status_code != 200:
                self.error(f"Unexpected Xquik response: {resp.status_code}")
                continue
            data = resp.json()
            name = data.get('name') or ''
            fname, mname, lname = parse_name(name)
            region = data.get('location')
            if any((fname, lname)):
                self.insert_contacts(
                    first_name=fname,
                    middle_name=mname,
                    last_name=lname,
                    title='X Profile',
                    region=region,
                )
