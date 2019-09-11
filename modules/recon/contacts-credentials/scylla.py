from recon.core.module import BaseModule


class Module(BaseModule):

    meta = {
        'name': 'Scylla Targetted Credential Harvester',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Harvests credentials from the scylla.sh API using email addresses as input. Updates the '
                       '\'credentials\' and \'contacts\' tables with the results.',
        'options': (
            ('size', 100, True, 'number of results per page'),
        ),
        'query': 'SELECT DISTINCT email FROM contacts WHERE email IS NOT NULL',
    }

    def module_run(self, emails):
        base_url = 'https://scylla.sh/search'
        headers = {'Accept': 'application/json'}
        size = self.options['size']
        for email in emails:
            page = 0
            while True:
                payload = {'q': f"Email:\"{email}\"", 'size': size, 'from': size*page}
                resp = self.request('GET', base_url, params=payload, headers=headers)
                if resp.status_code == 200:
                    creds = resp.json()
                    if not creds:
                        break
                    for cred in creds:
                        leak = cred['_source'].get('Domain')
                        username = cred['_source'].get('Email')
                        password = cred['_source'].get('Password')
                        passhash = cred['_source'].get('PassHash')
                        self.insert_credentials(username=username, password=password, _hash=passhash, leak=leak)
                    page+=1
                else:
                    self.error('Invalid response.')
                    break
