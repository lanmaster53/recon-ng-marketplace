from recon.core.module import BaseModule
import aes

def aes_decrypt(ciphertext, key, iv):
    decoded = ciphertext.decode('base64')
    password = aes.decryptData(key, iv.encode('utf-8') + decoded)
    return str(password, 'utf-8')

class Module(BaseModule):

    meta = {
        'name': 'PwnedList - Account Credentials Fetcher',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Queries the PwnedList API for credentials associated with the given usernames. Updates the \'credentials\' table with the results.',
        'required_keys': ['pwnedlist_api', 'pwnedlist_secret', 'pwnedlist_iv'],
        'comments': (
            'API Query Cost: 1 query per request and 1 query per unique leak.',
        ),
        'query': 'SELECT DISTINCT username FROM credentials WHERE username IS NOT NULL and password IS NULL',
        'dependencies': (
            'slowaes',
        ),
    }

    def module_run(self, accounts):
        key = self.keys.get('pwnedlist_api')
        secret = self.keys.get('pwnedlist_secret')
        decrypt_key = secret[:16]
        iv = self.keys.get('pwnedlist_iv')
        # setup the API call
        url = 'https://api.pwnedlist.com/api/1/accounts/query'
        # build the payload
        payload = {'account_identifier': ','.join(accounts), 'daysAgo': 0}
        payload = self.build_pwnedlist_payload(payload, 'accounts.query', key, secret)
        # make the request
        resp = self.request(url, payload=payload)
        if resp.json: jsonobj = resp.json
        else:
            self.error('Invalid JSON response.\n%s' % (resp.text))
            return
        if len(jsonobj['results']) == 0:
            self.output('No results returned.')
        else:
            # extract the credentials
            for cred in jsonobj['results']:
                username = cred['plain']
                password = aes_decrypt(cred['password'], decrypt_key, iv)
                leak = cred['leak_id']
                self.insert_credentials(username=username, password=password, leak=leak)
                self.insert_leaks(mute=True, **self.get_pwnedlist_leak(leak))
                self.query(f"DELETE FROM credentials WHERE username = '{username}' and password IS NULL and hash IS NULL")
