from recon.core.module import BaseModule
from urllib.parse import quote_plus
import time

class Module(BaseModule):

    meta = {
        'name': 'Have I been pwned? Breach Search',
        'author': 'Tim Tomes (@lanmaster53), Tyler Halfpop (@tylerhalfpop) and Geoff Pamerleau (@_geoff_p_)',
        'version': '1.2',
        'description': 'Leverages the haveibeenpwned.com API to determine if email addresses are associated with '
                       'breached credentials. Adds compromised email addresses to the \'credentials\' table.',
        'comments': (
            'The API is rate limited to 1 request per 1.5 seconds.',
        ),
        'required_keys': ['hibp_api'],
        'query': 'SELECT DISTINCT email FROM contacts WHERE email IS NOT NULL',
    }

    def module_run(self, accounts):
        # retrieve status
        headers = {'hibp-api-key': self.keys['hibp_api']}
        base_url = 'https://haveibeenpwned.com/api/v3/{}/{}?truncateResponse=false'
        endpoint = 'breachedaccount'
        for account in accounts:
            resp = self.request('GET', base_url.format(endpoint, quote_plus(account)), headers=headers)
            rcode = resp.status_code
            if rcode == 404:
                self.verbose(f"{account} => Not Found.")
            elif rcode == 400:
                self.error(f"{account} => Bad Request.")
                continue
            else:
                for breach in resp.json():
                    self.alert(f"{account} => Breach found! Seen in the {breach['Name']} breach that occurred on "
                               f"{breach['BreachDate']}.")
                    self.insert_credentials(username=account, leak=breach['Name'])
            time.sleep(1.6)
