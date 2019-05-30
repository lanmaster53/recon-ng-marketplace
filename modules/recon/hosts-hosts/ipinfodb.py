from recon.core.module import BaseModule
import json
import time

class Module(BaseModule):

    meta = {
        'name': 'IPInfoDB GeoIP',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Leverages the ipinfodb.com API to geolocate a host by IP address. Updates the \'hosts\' table with the results.',
        'required_keys': ['ipinfodb_api'],
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
    }
   
    def module_run(self, hosts):
        api_key = self.keys.get('ipinfodb_api')
        for host in hosts:
            url = (f"http://api.ipinfodb.com/v3/ip-city/?key={api_key}&ip={host}&format=json")
            resp = self.request(url)
            try:
                jsonobj = resp.json()
            except ValueError:
                self.error(f"Invalid JSON response for '{host}'.\n{resp.text}")
                continue
            if jsonobj['statusCode'].lower() == 'error':
                self.error(jsonobj['statusMessage'])
                continue
            time.sleep(1.5)
            # Used to catch the garbage data and null it out so it does not clog up the database.
            for x in ['cityName', 'regionName', 'countryName', 'latitude', 'longitude']:
                if jsonobj[x] == '-' or jsonobj[x] == '0':
                    jsonobj[x] = None

            region = ', '.join([jsonobj[x] for x in ['cityName', 'regionName'] if jsonobj[x]]) or None
            country = jsonobj['countryName']
            latitude = jsonobj['latitude']
            longitude = jsonobj['longitude']
            self.output(f"{host} - {latitude},{longitude} - {', '.join([x for x in [region, country] if x])}")
            self.query('UPDATE hosts SET region=?, country=?, latitude=?, longitude=? WHERE ip_address=?', (region, country, latitude, longitude, host))
