from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'Address Geocoder',
        'author': 'Quentin Kaiser (contact@quentinkaiser.be)',
        'version': '1.0',
        'description': 'Queries the Google Maps API to obtain coordinates for an address. Updates the \'locations\' table with the results.',
        'required_keys': ['google_api'],
        'query': 'SELECT DISTINCT street_address FROM locations WHERE street_address IS NOT NULL',
    }

    def module_run(self, addresses):
        api_key = self.keys.get('google_api')
        for address in addresses:
            self.verbose(f"Geocoding '{address}'...")
            payload = {'address' : address, 'key' : api_key}
            url = 'https://maps.googleapis.com/maps/api/geocode/json'
            resp = self.request('GET', url, params=payload)
            # kill the module if nothing is returned
            if len(resp.json()['results']) == 0:
                self.output(f"Unable to geocode '{address}'.")
                return
            # loop through the results
            for result in resp.json()['results']:
                lat = result['geometry']['location']['lat']
                lon = result['geometry']['location']['lng']
                # store the result
                self.insert_locations(lat, lon, address)
            self.query('DELETE FROM locations WHERE street_address=? AND latitude IS NULL AND longitude IS NULL', (address,))
