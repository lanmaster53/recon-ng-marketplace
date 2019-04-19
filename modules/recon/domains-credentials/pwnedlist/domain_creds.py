from recon.core.module import BaseModule
import aes

def aes_decrypt(ciphertext, key, iv):
    decoded = ciphertext.decode('base64')
    password = aes.decryptData(key, iv.encode('utf-8') + decoded)
    return str(password, 'utf-8')

class Module(BaseModule):

    meta = {
        'name': 'PwnedList - Pwned Domain Credentials Fetcher',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Queries the PwnedList API to fetch all credentials for a domain. Updates the \'credentials\' table with the results.',
        'required_keys': ['pwnedlist_api', 'pwnedlist_secret', 'pwnedlist_iv'],
        'comments': (
            'API Query Cost: 10,000 queries per request, 1 query for each account returned, and 1 query per unique leak.',
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'dependencies': (
            'slowaes',
        ),
    }

    def module_run(self, domains):
        key = self.keys.get('pwnedlist_api')
        secret = self.keys.get('pwnedlist_secret')
        decrypt_key = secret[:16]
        iv = self.keys.get('pwnedlist_iv')
        # setup the API call
        url = 'https://api.pwnedlist.com/api/1/domains/query'
        for domain in domains:
            self.heading(domain, level=0)
            payload = {'domain_identifier': domain, 'daysAgo': 0}
            while True:
                # build the payload
                pwnedlist_payload = self.build_pwnedlist_payload(payload, 'domains.query', key, secret)
                # make the request
                resp = self.request(url, payload=pwnedlist_payload)
                if resp.json: jsonobj = resp.json
                else:
                    self.error('Invalid JSON response for \'%s\'.\n%s' % (domain, resp.text))
                    break
                if len(jsonobj['accounts']) == 0:
                    self.output(f"No results returned for '{domain}'.")
                    break
                # extract the credentials
                for cred in jsonobj['accounts']:
                    username = cred['plain']
                    password = aes_decrypt(cred['password'], decrypt_key, iv)
                    leak = cred['leak_id']
                    self.insert_credentials(username=username, password=password, leak=leak)
                    self.insert_leaks(mute=True, **self.get_pwnedlist_leak(leak))
                # paginate
                if jsonobj['token']:
                    payload['token'] = jsonobj['token']
                    continue
                break
