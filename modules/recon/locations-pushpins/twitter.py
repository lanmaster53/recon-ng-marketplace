from recon.core.module import BaseModule
from recon.mixins.twitter import TwitterMixin
from datetime import datetime

class Module(BaseModule, TwitterMixin):

    meta = {
        'name': 'Twitter Geolocation Search',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.1',
        'description': 'Searches Twitter for media in the specified proximity to a location.',
        'required_keys': ['twitter_api', 'twitter_secret'],
        'query': 'SELECT DISTINCT latitude || \',\' || longitude FROM locations WHERE latitude IS NOT NULL AND longitude IS NOT NULL',
        'options': (
            ('radius', 1, True, 'radius in kilometers'),
        ),
    }

    def module_run(self, points):
        rad = self.options['radius']
        for point in points:
            self.heading(point, level=0)
            self.output('Collecting data for an unknown number of tweets...')
            results = self.search_twitter_api({'q':'', 'geocode': f"{point},{rad}km", 'count':'100'})
            for tweet in results:
                if not tweet['geo']:
                    continue
                tweet_id = tweet['id_str']
                source = 'Twitter'
                screen_name = tweet['user']['screen_name']
                profile_name = tweet['user']['name']
                profile_url = f"https://twitter.com/{screen_name}"
                media_url = f"https://twitter.com/{screen_name}/statuses/{tweet_id}"
                thumb_url = tweet['user']['profile_image_url_https']
                message = tweet['text']
                latitude = tweet['geo']['coordinates'][0]
                longitude = tweet['geo']['coordinates'][1]
                time = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')
                self.insert_pushpins(source, screen_name, profile_name, profile_url, media_url, thumb_url, message, latitude, longitude, time)
            self.verbose(f"{len(results)} tweets processed.")
