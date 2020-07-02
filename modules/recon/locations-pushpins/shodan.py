from recon.core.module import BaseModule
import shodan
import time
from datetime import datetime


def prep_host(host_data, hostname):
    os = host_data['os']
    hostname = hostname
    host_port = f"{host_data['ip_str']}:{host_data['port']}"
    source = 'Shodan'
    screen_name = host_port
    profile_name = host_port
    profile_url = f"http://{host_port}"
    media_url = f"https://www.shodan.io/host/{host_data['ip_str']}"
    thumb_url = 'https://gravatar.com/avatar/ffc4048d63729d4932fd3cc45139174f?s=300'
    message = (
        f"Hostname: {hostname} | City: {host_data['location']['city']} | State: {host_data['location']['region_code']} "
        f"| Country: {host_data['location']['country_name']} | OS: {os}")
    latitude = host_data['location']['latitude']
    longitude = host_data['location']['longitude']
    time = datetime.strptime(host_data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
    return source, screen_name, profile_name, profile_url, media_url, thumb_url, message, latitude, longitude, time


class Module(BaseModule):

    meta = {
        'name': 'Shodan Geolocation Search',
        'author': 'Tim Tomes (@lanmaster53) & Ryan Hays (@_ryanhays)',
        'version': '1.1',
        'description': 'Searches Shodan for media in the specified proximity to a location.',
        'required_keys': ['shodan_api'],
        'comments': (
            'Shodan \'geo\' searches can take a long time to complete. If receiving timeout errors, increase the global'
            ' TIMEOUT option.',
        ),
        'query': 'SELECT DISTINCT latitude || \',\' || longitude FROM locations WHERE latitude IS NOT NULL AND '
                 'longitude IS NOT NULL',
        'options': (
            ('radius', 1, True, 'radius in kilometers'),
            ('limit', 1, True, 'limit number of api requests per input source (0 = unlimited)'),
        ),
        'dependencies': ['shodan']
    }

    def module_run(self, points):
        limit = self.options['limit']
        rad = self.options['radius']
        api = shodan.Shodan(self.keys.get('shodan_api'))

        for point in points:
            self.heading(point, level=0)
            query = f"geo:{point},{rad}"

            try:
                page = 1
                rec_count = 0
                total_results = 1
                while rec_count < total_results:
                    results = api.search(query, page=page)
                    total_results = results['total']

                    for host in results['matches']:
                        rec_count += 1
                        if len(host['hostnames']) > 0:
                            for hostname in host['hostnames']:
                                self.insert_pushpins(*prep_host(host, hostname))
                        else:
                            self.insert_pushpins(*prep_host(host, 'None'))

                    page += 1
                    time.sleep(limit)

            except shodan.exception.APIError:
                pass
