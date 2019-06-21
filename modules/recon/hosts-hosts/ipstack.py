from recon.core.module import BaseModule
import json

class Module(BaseModule):

    meta = {
        'name': 'ipstack',
        'author': 'Siarhei Harbachou (Tech.Insiders), Gerrit Helm (G) and Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Leverages the ipstack.com API to geolocate a host by IP address. Updates the \'hosts\' table with the results.',
        'required_keys': ['ipstack_api'],
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
    }

    def module_run(self, hosts):
        for host in hosts:
            api_key = self.keys.get('ipstack_api')
            url = f"http://api.ipstack.com/{host}?access_key={api_key}"
            resp = self.request('GET', url)
            try:
                jsonobj = resp.json()
            except ValueError:
                self.error(f"Invalid JSON response for '{host}'.\n{resp.text}")
                continue
            region = ', '.join([jsonobj[x] for x in ['city', 'region_name'] if jsonobj[x]]) or None
            country = jsonobj['country_name']
            latitude = jsonobj['latitude']
            longitude = jsonobj['longitude']
            self.output(f"{host} - {latitude},{longitude} - {', '.join([x for x in [region, country] if x])}")
            self.query('UPDATE hosts SET region=?, country=?, latitude=?, longitude=? WHERE ip_address=?', (region, country, latitude, longitude, host))
