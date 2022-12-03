# module required for framework integration
from recon.core.module import BaseModule


class Module(BaseModule):

    meta = {
        'name': 'DeHashed Domain Search',
        'author': '@TheToddLuci0',
        'version': '0.0.1',
        'description': 'Gather exposed hashes from DeHashed.com for a domain, store them in the credentials table.',
        'required_keys': ['dehashed_api', 'dehashed_email'],
        'options': (
                ('req_per_sec', '5', 'yes',
                 'Number of requests per second to make. DeGHashed default is 5.'),
                ('page_size', '10000', 'yes',
                 'Number of requests per page. Higher number = less credis used, lower = faster per query.'),
                ('everything', False, 'yes',
                 'Include everything. This will probably fill your database with garbage.')
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL'
    }

    def load_creds(self, creds):
        for e in creds:
            username = e['username'] if e['username'] != '' else e['email']
            if self.options['everything'] or e['password'] != '' or '@' in e['username']:
                self.insert_credentials(
                    username=username, password=e['password'], notes="dehashed id: {}".format(e['id']))

    def module_run(self, domains):
        auth = (self.keys['dehashed_email'], self.keys['dehashed_api'].lower())
        for d in domains:
            req = 1
            q = 'email:/.+@{}/'.format(d)
            r = self.request('GET', 'https://api.dehashed.com/search?query={}&size={}'.format(
                q, self.options['page_size']), auth=auth, headers={'accept': 'application/json'})
            if r.status_code != 200:
                self.print_exception(line=r.content)
                return
            self.verbose('Dehashed balance: {}'.format(r.json()['balance']))
            self.load_creds(r.json()['entries'])
            while (req * self.options['page_size']) < r.json()['total']:
                req += 1
                r = self.request('GET', 'https://api.dehashed.com/search?query={}&size={}&page={}'.format(
                    q, self.options['page_size'], req), auth=auth, headers={'accept': 'application/json'})
                if r.status_code != 200:
                    self.print_exception(line=r.content)
                    return
                self.verbose('Dehashed balance: {}'.format(
                    r.json()['balance']))
                self.load_creds(r.json()['entries'])
