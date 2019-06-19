from recon.core.module import BaseModule
import time

class Module(BaseModule):

    meta = {
        'name': 'Jigsaw - Single Contact Retriever',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Retrieves a single complete contact from the Jigsaw.com API using points from the given account.',
        'required_keys': ['jigsaw_username', 'jigsaw_password', 'jigsaw_api'],
        'comments': (
            'Account Point Cost: 5 points per request.',
            'This module is typically used to validate email address naming conventions and gather alternative social engineering information.',
        ),
        'options': (
            ('contact', None, True, 'jigsaw contact id'),
        ),
    }

    def module_run(self):
        username = self.keys.get('jigsaw_username')
        password = self.keys.get('jigsaw_password')
        key = self.keys.get('jigsaw_api')
        url = f"https://www.jigsaw.com/rest/contacts/{self.options['contact']}.json"
        payload = {'token': key, 'username': username, 'password': password, 'purchaseFlag': 'true'}
        resp = self.request('GET', url, params=payload, allow_redirects=False)
        try:
            jsonobj = resp.json()
        except ValueError:
            self.error(f"Invalid JSON response.\n{resp.text}")
            return
        # handle output
        contacts = jsonobj['contacts']
        header = ['Item', 'Info']
        for contact in contacts:
            tdata = []
            for key in contact:
                tdata.append((key.title(), contact[key]))
            self.table(tdata, header=header, title=f"Jigsaw {contact['contactId']}")
