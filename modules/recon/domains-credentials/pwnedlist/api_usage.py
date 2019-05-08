from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'PwnedList - API Usage Statistics Fetcher',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Queries the PwnedList API for account usage statistics.',
        'required_keys': ['pwnedlist_api', 'pwnedlist_secret'],
    }

    def module_run(self):
        key = self.keys.get('pwnedlist_api')
        secret = self.keys.get('pwnedlist_secret')
        # setup the API call
        url = 'https://api.pwnedlist.com/api/1/usage/info'
        payload = {}
        payload = self.build_pwnedlist_payload(payload, 'usage.info', key, secret)
        # make the request
        resp = self.request(url, payload=payload)
        try:
            jsonobj = resp.json()
        except ValueError:
            self.error(f"Invalid JSON response.\n{resp.text}")
            return
        # handle the output
        total = jsonobj['num_queries_allotted']
        left = jsonobj['num_queries_left']
        self.output(f"Queries allotted:  {total}")
        self.output(f"Queries remaining: {left}")
        self.output(f"Queries used:      {total-left}")
