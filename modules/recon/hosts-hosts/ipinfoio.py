from recon.core.module import BaseModule
from recon.mixins.threads import ThreadingMixin

class Module(BaseModule, ThreadingMixin):

    meta = {
        'name': 'IPInfo.io info',
        'author': 'Jan-Jaap Korpershoek (@JJK96)',
        'version': '1.0',
        'description': 'Leverages the ipinfo.io API to geolocate a host by IP address. Updates the \'hosts\' table '
                       'with the results.',
        'required_keys': [],
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
        'options': ( ),
        'comments': (
            'Free API access is limited to 50.000 requests per month.',
            'If you are getting a 429 error, implement token authentication in this module.',
        ),
    }

    def module_run(self, hosts):
        self.thread(hosts)

    def module_thread(self, host):
        url = f"https://ipinfo.io/{host}/json"
        resp = self.request('GET', url)
        try:
            jsonobj = resp.json()
        except ValueError:
            self.error(f"Invalid JSON response for '{host}'.\n{resp.text}")
            return
        if 'error' in jsonobj:
            self.error(jsonobj['error']['message'])
            return

        region = ', '.join([jsonobj[x] for x in ['city', 'region'] if jsonobj[x]]) or None
        country = jsonobj['country']
        organization = jsonobj['org']
        latitude, longitude = jsonobj['loc'].split(',')
        self.output(f"{host} - {latitude},{longitude} - {', '.join([x for x in [region, country] if x])}")
        self.query('UPDATE hosts SET region=?, country=?, latitude=?, longitude=?, organization=? WHERE ip_address=?',
                   (region, country, latitude, longitude, organization, host))
