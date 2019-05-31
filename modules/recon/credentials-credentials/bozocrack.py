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
            'Available Algorithms: {}'.format(', '.join(hashlib.algorithms_available)),
        ),
        'query': 'SELECT DISTINCT hash FROM credentials WHERE hash IS NOT NULL AND password IS NULL AND type IS NOT \'Adobe\'',
        'options': (
            ('algorithms', 'md5, sha1, sha256, sha512', True, 'Comma separated list of hashing algorithms to use. Supported list is below.'),
        ),
    }

    def module_run(self, hashes):
        url = 'http://www.google.com/search'
        hashlist = []
        for hash in self.options['algorithms'].split(','):
            try:
                getattr(hashlib, hash.strip())
                hashlist.append(hash.strip())
            except AttributeError:
                self.error(f"{hash.strip()} is not supported.")
                continue

        for hashstr in hashes:
            payload = {'q': hashstr}
            resp = self.request(url, payload=payload, redirect=False)
            if resp.status_code != 200:
                if resp.status_code == 302:
                    self.error('You\'ve been temporarily banned by Google for violating the terms of service.')
                else:
                    self.error('Google has encountered an error.')
                break

            wordlist = set(resp.text.replace('.', ' ').replace(':', ' ').replace('?', '').split(' '))
            plaintext, hashtype = crack(hashstr, wordlist, hashlist)
            if plaintext:
                self.alert(f"{hashstr} ({hashtype}) => {plaintext}")
                self.query(f"UPDATE credentials SET password='{plaintext}', type='{hashtype}' WHERE hash='{hashstr}'")
            else:
                self.verbose(f"Value not found for hash: {hashstr}")
            # sleep to avoid lock-out
            time.sleep(random.randint(3,5))


def crack(hashstr, wordlist, hashlist):
    for word in wordlist:
        for hashtype in hashlist:
            func = getattr(hashlib, hashtype)
            try:
                if func(word.encode('utf-8')).hexdigest().lower() == hashstr.lower():
                    return word, hashtype
            except TypeError:
                continue
    return None, None
