from recon.core.module import BaseModule
from recon.mixins.pwnedlist import PwnedlistMixin
import base64
import pyaes

def aes_encrypt(plaintext, key, iv):
    iv = iv.encode('utf-8')
    key = key.encode('utf-8')
    aes = pyaes.AESModeOfOperationCBC(key, iv=iv)
    ciphertext = aes.encrypt(plaintext)
    return base64.b64encode(ciphertext)

def aes_decrypt(ciphertext, key, iv):
    ciphertext = base64.b64decode(ciphertext)
    iv = iv.encode('utf-8')
    key = key.encode('utf-8')
    aes = pyaes.AESModeOfOperationCBC(key, iv=iv)
    plaintext = aes.decrypt(ciphertext)
    return plaintext.decode("utf-8")

class Module(BaseModule, PwnedlistMixin):

    meta = {
        'name': 'PwnedList - Account Credentials Fetcher',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Queries the PwnedList API for credentials associated with the given usernames. Updates the \'credentials\' table with the results.',
        'required_keys': ['pwnedlist_api', 'pwnedlist_secret', 'pwnedlist_iv'],
        'comments': (
            'API Query Cost: 1 query per request and 1 query per unique leak.',
        ),
        'query': 'SELECT DISTINCT username FROM credentials WHERE username IS NOT NULL and password IS NULL',
        'dependencies': (
            'pyaes',
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
        resp = self.request('GET', url, params=payload)
        try:
            jsonobj = resp.json()
        except ValueError:
            self.error(f"Invalid JSON response.\n{resp.text}")
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
