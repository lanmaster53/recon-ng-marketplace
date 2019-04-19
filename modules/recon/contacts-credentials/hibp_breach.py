from recon.core.module import BaseModule
import time
import urllib.request, urllib.parse, urllib.error

class Module(BaseModule):

    meta = {
        'name': 'Have I been pwned? Breach Search',
        'author': 'Tim Tomes (@LaNMaSteR53) & Tyler Halfpop (@tylerhalfpop)',
        'version': '1.0',
        'description': 'Leverages the haveibeenpwned.com API to determine if email addresses are associated with breached credentials. Adds compromised email addresses to the \'credentials\' table.',
        'comments': (
            'The API is rate limited to 1 request per 1.5 seconds.',
        ),
        'query': 'SELECT DISTINCT email FROM contacts WHERE email IS NOT NULL',
    }

    def module_run(self, accounts):
        # retrieve status
        base_url = 'https://haveibeenpwned.com/api/v2/%s/%s'
        endpoint = 'breachedaccount'
        for account in accounts:
            resp = self.request(base_url % (endpoint, urllib.parse.quote(account)))
            rcode = resp.status_code
            if rcode == 404:
                self.verbose(f"{account} => Not Found.")
            elif rcode == 400:
                self.error(f"{account} => Bad Request.")
                continue
            else:
                for breach in resp.json:
                    self.alert(f"{account} => Breach found! Seen in the {breach['Title']} breach that occurred on {breach['BreachDate']}.")
                self.insert_credentials(account)
            time.sleep(1.6)
