from recon.core.module import BaseModule
import hashlib
import random
import time


class Module(BaseModule):

    meta = {
        'name': 'PyBozoCrack Hash Lookup',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Searches Google for the value of a hash and tests for a match by hashing every word in the resulting page using all hashing algorithms supported by the \'hashlib\' library. Updates the \'credentials\' table with the positive results.',
        'comments': (
            'Inspired by the PyBozoCrack script: https://github.com/ikkebr/PyBozoCrack',
            f"Available Algorithms: {', '.join(hashlib.algorithms_available)}",
        ),
        'query': 'SELECT DISTINCT hash FROM credentials WHERE hash IS NOT NULL AND password IS NULL AND type IS NOT \'Adobe\'',
        'options': (
            ('algorithms', 'md5, sha1, sha256, sha512', True, 'Comma separated list of hashing algorithms to use. See comments for a list of available algorithms.'),
        ),
    }

    def module_run(self, hashes):
        url = 'http://www.google.com/search'
        hashlist = []
        for hash in [x.strip() for x in self.options['algorithms'].split(',')]:
            try:
                hashlist.append(getattr(hashlib, hash))
            except AttributeError:
                self.error(f"{hash} is not supported.")
        # exit if no supported algorithms
        if not hashlist:
            self.alert('No valid algorithms provided.')
            return

        for hashstr in hashes:
            payload = {'q': hashstr}
            resp = self.request('GET', url, params=payload, allow_redirects=False)
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
        for hashfunc in hashlist:
            try:
                if hashfunc(word.encode('utf-8')).hexdigest().lower() == hashstr.lower():
                    return word, hashtype
            except TypeError:
                continue
    return None, None
