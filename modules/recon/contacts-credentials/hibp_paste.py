from recon.core.module import BaseModule
import os
import time
import urllib.request, urllib.parse, urllib.error

class Module(BaseModule):

    meta = {
        'name': 'Have I been pwned? Paste Search',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Leverages the haveibeenpwned.com API to determine if email addresses have been published to various paste sites. Adds compromised email addresses to the \'credentials\' table.',
        'comments': (
            'Paste sites supported: Pastebin, Pastie, Slexy, Ghostbin, QuickLeak, JustPaste, AdHocUrl, and OptOut.'
            'The HIBP API is rate limited to 1 request per 1.5 seconds.',
        ),
        'query': 'SELECT DISTINCT email FROM contacts WHERE email IS NOT NULL',
        'options': (
            ('download', True, True, 'download pastes'),
        ),
    }

    def module_run(self, accounts):
        # check back often for new paste sources
        sites = {
            'Pastebin': 'http://pastebin.com/raw.php?i=%s',
            'Pastie': 'http://pastie.org/pastes/%s/text',
            'Slexy': 'http://slexy.org/raw/%s',
            'Ghostbin': 'https://ghostbin.com/paste/%s/raw',
            'QuickLeak': 'http://www.quickleak.ir/%s',
            'JustPaste': 'https://justpaste.it/%s',
            'AdHocUrl': '%s',
            }
        # retrieve status
        base_url = 'https://haveibeenpwned.com/api/v2/%s/%s'
        endpoint = 'pasteaccount'
        for account in accounts:
            resp = self.request(base_url % (endpoint, urllib.parse.quote(account)))
            rcode = resp.status_code
            if rcode == 404:
                self.verbose(f"{account} => Not Found.")
            elif rcode == 400:
                self.error(f"{account} => Bad Request.")
                continue
            else:
                for paste in resp.json:
                    download = False
                    fileurl = paste['Id']
                    if paste['Source'] in sites:
                        fileurl = sites[paste['Source']] % (paste['Id'])
                        download = self.options['download']
                    elif self.options['download'] == True:
                        self.alert('Download not available for %s pastes.' % (paste['Source']))
                    self.alert(f"{account} => Paste found! Seen in a {paste['Source']} on {paste['Date']} ({fileurl}).")
                    if download == True:
                        resp = self.request(fileurl)
                        if resp.status_code == 200:
                            filepath = f"{self.workspace}/{_safe_file_name(fileurl)}.txt"
                            if not os.path.exists(filepath):
                                dl = open(filepath, 'w')
                                dl.write(resp.text.encode(resp.encoding) if resp.encoding else resp.text)
                                dl.close()
                            self.verbose(f"Paste stored at '{filepath}'.")
                        else:
                            self.alert(f"Paste could not be downloaded ({fileurl}).")
                self.insert_credentials(account)
            time.sleep(1.6)

def _safe_file_name(s):
    return "".join(c for c in s if c.isalnum()).rstrip()
