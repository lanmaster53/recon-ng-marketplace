import os
import time

from recon.core.module import BaseModule
from requests.exceptions import ConnectionError
from urllib.parse import quote_plus


class Module(BaseModule):

    meta = {
        'name': 'Have I been pwned? Paste Search',
        'author': 'Tim Tomes (@lanmaster53) and Geoff Pamerleau (@_geoff_p_)',
        'version': '1.1',
        'description': 'Leverages the haveibeenpwned.com API to determine if email addresses have been published to '
                       'various paste sites. Adds compromised email addresses to the \'credentials\' table.',
        'comments': (
            'Paste sites supported: Pastebin, Pastie, Slexy, Ghostbin, QuickLeak, JustPaste, AdHocUrl, and OptOut.'
            'The HIBP API is rate limited to 1 request per 1.5 seconds.',
        ),
        'query': 'SELECT DISTINCT email FROM contacts WHERE email IS NOT NULL',
        'required_keys': ['hibp_api'],
        'options': (
            ('download', True, True, 'download pastes'),
        ),
    }

    def module_run(self, accounts):
        # check back often for new paste sources
        headers = {'hibp-api-key': self.keys['hibp_api']}
        sites = {
            'Pastebin': 'http://pastebin.com/raw.php?i={}',
            'Pastie': 'http://pastie.org/pastes/{}/text',
            'Slexy': 'http://slexy.org/raw/{}',
            'Ghostbin': 'https://ghostbin.com/paste/{}/raw',
            'QuickLeak': 'http://www.quickleak.ir/{}',
            'JustPaste': 'https://justpaste.it/{}',
            'AdHocUrl': '{}',
            }
        # retrieve status
        base_url = 'https://haveibeenpwned.com/api/v3/{}/{}'
        endpoint = 'pasteaccount'
        for account in accounts:
            resp = self.request('GET', base_url.format(endpoint, quote_plus(account)), headers=headers)
            rcode = resp.status_code
            if rcode == 404:
                self.verbose(f"{account} => Not Found.")
            elif rcode == 400:
                self.error(f"{account} => Bad Request.")
                continue
            else:
                for paste in resp.json():
                    download = False
                    fileurl = paste['Id']
                    if paste['Source'] in sites:
                        fileurl = sites[paste['Source']].format(paste['Id'])
                        download = self.options['download']
                    elif self.options['download']:
                        self.alert(f"Download not available for {paste['Source']} pastes.")
                    self.alert(f"{account} => Paste found! Seen in a {paste['Source']} on {paste['Date']} ({fileurl}).")
                    if download:
                        try:
                            resp = self.request('GET', fileurl)
                        except ConnectionError:
                            self.alert(f"Paste could not be downloaded ({fileurl}).")

                        if resp.status_code == 200:
                            filepath = f"{self.workspace}/{_safe_file_name(fileurl)}.txt"
                            if not os.path.exists(filepath):
                                dl = open(filepath, 'wb')
                                dl.write(resp.content)
                                dl.close()
                            self.verbose(f"Paste stored at '{filepath}'.")
                        else:
                            self.alert(f"Paste could not be downloaded ({fileurl}).")
                self.insert_credentials(account)
            time.sleep(1.6)

def _safe_file_name(s):
    return "".join(c for c in s if c.isalnum()).rstrip()
