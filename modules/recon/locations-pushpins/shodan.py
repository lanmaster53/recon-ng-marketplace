from recon.core.module import BaseModule
from recon.mixins.search import ShodanAPIMixin
from datetime import datetime

class Module(BaseModule, ShodanAPIMixin):

    meta = {
        'name': 'Shodan Geolocation Search',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Searches Shodan for media in the specified proximity to a location.',
        'required_keys': ['shodan_api'],
        'comments': (
            'Shodan \'geo\' searches can take a long time to complete. If receiving connection timeout errors, increase the global SOCKET_TIMEOUT option.',
        ),
        'query': 'SELECT DISTINCT latitude || \',\' || longitude FROM locations WHERE latitude IS NOT NULL AND longitude IS NOT NULL',
        'options': (
            ('radius', 1, True, 'radius in kilometers'),
            ('limit', 1, True, 'limit number of api requests per input source (0 = unlimited)'),
        ),
    }

    def module_run(self, points):
        limit = self.options['limit']
        rad = self.options['radius']
        for point in points:
            self.heading(point, level=0)
            query = f"geo:{point},{rad}"
            results = self.search_shodan_api(query, limit)
            for host in results:
                os = host['os'] if 'os' in host else ''
                hostname = host['hostnames'][0] if len(host['hostnames']) > 0 else 'None'
                protocol = f"{host['ip_str']}:{host['port']}"
                source = 'Shodan'
                screen_name = protocol
                profile_name = protocol
                profile_url = f"http://{protocol}"
                media_url = f"https://www.shodan.io/host/{host['ip_str']}"
                thumb_url = 'https://gravatar.com/avatar/ffc4048d63729d4932fd3cc45139174f?s=300'
                message = (f"Hostname: {hostname} | City: {host['location']['city']}, {host['location']['country_name']} | OS: {os}")
                latitude = host['location']['latitude']
                longitude = host['location']['longitude']
                time = datetime.strptime(host['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
                self.insert_pushpins(source, screen_name, profile_name, profile_url, media_url, thumb_url, message, latitude, longitude, time)
