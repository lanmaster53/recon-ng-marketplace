from recon.core.module import BaseModule
from recon.mixins.oauth import ExplicitOauthMixin
from datetime import datetime

class Module(BaseModule, ExplicitOauthMixin):

	meta = {
		'name': 'VKontakte Geolocation Search',
		'Author': 'Andrey Zhukov from USSC',
		'description': 'Searches vkontakte for media in the specified proximity to a location.',
		'required_keys': ['vkontakte_api', 'vkontakte_secret'],
		'comments': (
			'Radius must be greater than zero and less than 50000 meters.',
		),
		'query': 'SELECT DISTINCT latitude || \',\' || longitude FROM locations WHERE latitude IS NOT NULL AND longitude IS NOT NULL',
		'options': (
			('radius', 50, True, 'radius in meters'),
			('start_time', 0, False, 'start time (d.m.Y H:M:S)'),
			('end_time', 0, False, 'end time (d.m.Y H:M:S)')
		),
	}

	def get_vkontakte_access_token(self):
		return self.get_explicit_oauth_token(
			'vkontakte',
			'friends',
			'https://oauth.vk.com/authorize',
			'https://oauth.vk.com/access_token'
		)

	def module_run(self, points):
		access_token = self.get_vkontakte_access_token()
		if not access_token:
			return

		url = 'https://api.vk.com/method/photos.search.json'
		rad = self.options['radius']
		start_time = datetime.strptime(self.options['start_time'], '%d.%m.%Y %H:%M:%S').strftime("%s") if self.options['start_time'] else 0
		end_time = datetime.strptime(self.options['end_time'], '%d.%m.%Y %H:%M:%S').strftime("%s") if self.options['end_time'] else 0
		for point in points:
			self.heading(point, level=0)
			lat = point.split(',')[0]
			lon = point.split(',')[1]
			offset = 0
			while True:
				params = {'lat': lat, 'long': lon, 'radius': rad, 'count': 100, 'offset': offset, 'start_time': start_time, 'end_time': end_time, 'access_token': access_token, 'v': 5.103 }
				resp = self.request('GET', url, params=params)
				if not resp.json()["response"]["items"]:
					break
				for pushpin in resp.json()["response"]["items"]:
					offset += 1
					source = "vk"
					screen_name = pushpin.get('id')
					profile_name = pushpin.get('owner_id')
					profile_url = "https://vk.com/id%d" % profile_name if profile_name > 0 else "https://vk.com/public%d" % abs(profile_name)
					max_size = 0
					for image in pushpin["sizes"]:
						if image.get("width") * image.get("height") > max_size:
							media_url = image.get("url")
					thumb_url = pushpin.get('src') or ''
					message = pushpin.get('text') or ''
					latitude = pushpin.get('lat') or ''
					longitude = pushpin.get('long') or ''
					time = datetime.fromtimestamp( pushpin.get('created') or 0 )
					if latitude and longitude:
						self.insert_pushpins(source, '', '', profile_url, media_url, thumb_url, message, latitude, longitude, time)
