from recon.core.module import BaseModule
import hashlib
import random
import time

class Module(BaseModule):

    meta = {
        'name': 'PyBozoCrack Hash Lookup',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Searches Google for the value of a hash and tests for a match by hashing every word in the resulting page using all hashing algorithms supported by the \'hashlib\' library. Updates the \'credentials\' table with the positive results.',
        'comments': (
            'Inspired by the PyBozoCrack script: https://github.com/ikkebr/PyBozoCrack',
        ),
        'query': 'SELECT DISTINCT hash FROM credentials WHERE hash IS NOT NULL AND password IS NULL AND type IS NOT \'Adobe\'',
    }

    def module_run(self, hashes):
        url = 'http://www.google.com/search'
        for hashstr in hashes:
            payload = {'q': hashstr}
            resp = self.request(url, payload=payload, redirect=False)
            if resp.status_code != 200:
                if resp.status_code == 302:
                    self.error('You\'ve been temporarily banned by Google for violating the terms of service.')
                else:
                    self.error('Google has encountered an error.')
                break
            #re.sub('[\.:?]', ' ', resp.text).split()
            wordlist = set(resp.raw.replace('.', ' ').replace(':', ' ').replace('?', '').split(' '))
            plaintext, hashtype = crack(hashstr, wordlist)
            if plaintext:
                self.alert(f"{hashstr} ({hashtype}) => {plaintext}")
                self.query(f"UPDATE credentials SET password='{plaintext}', type='{hashtype}' WHERE hash='{hashstr}'")
            else:
                self.verbose(f"Value not found for hash: {hashstr}")
            # sleep to avoid lock-out
            time.sleep(random.randint(3,5))

def crack(hashstr, wordlist):
    for word in wordlist:
        for hashtype in hashlib.algorithms:
            func = getattr(hashlib, hashtype)
            if func(word).hexdigest().lower() == hashstr.lower():
                return word, hashtype
    return None, None
