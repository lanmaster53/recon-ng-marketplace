import time

from recon.core.module import BaseModule


class Module(BaseModule):

    meta = {
        'name': 'Scylla Targetted Credential Harvester',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.4',
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
        start = 0
        for email in emails:
            while True:
                payload = {'q': f"email:\"{email}\"", 'size': size, 'start': start}
                resp = self.request('GET', base_url, params=payload, headers=headers, auth=('sammy', 'BasicPassword!'))
                if resp.status_code != 200:
                    self.error('Invalid response.')
                    break
                creds = resp.json()
                if not creds:
                    break
                for cred in creds:
                    leak = cred['fields'].get('domain')
                    username = cred['fields'].get('email')
                    password = cred['fields'].get('password')
                    passhash = cred['fields'].get('passHash')
                    self.insert_credentials(username=username, password=password, _hash=passhash, leak=leak)
                start = start + size
                if start >= 10000:
                    self.alert('Limit reached.')
                    break
                time.sleep(0.5)
