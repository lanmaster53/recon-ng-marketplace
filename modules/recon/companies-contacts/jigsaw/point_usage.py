from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'Jigsaw - Point Usage Statistics Fetcher',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Queries the Jigsaw API for the point usage statistics of the given account.',
        'required_keys': ['jigsaw_username', 'jigsaw_password', 'jigsaw_api'],
    }

    def module_run(self):
        username = self.keys.get('jigsaw_username')
        password = self.keys.get('jigsaw_password')
        key = self.keys.get('jigsaw_api')
        url = 'https://www.jigsaw.com/rest/user.json'
        payload = {'token': key, 'username': username, 'password': password}
        resp = self.request(url, payload=payload, redirect=False)
        try:
            jsonobj = resp.json()
        except ValueError:
            self.error(f"Invalid JSON response.\n{resp.text}")
            return
        # handle output
        self.output(f"{jsonobj['points']} Jigsaw points remaining.")
