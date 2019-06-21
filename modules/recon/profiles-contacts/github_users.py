from recon.core.module import BaseModule
from recon.mixins.github import GithubMixin
from recon.utils.parsers import parse_name
from urllib.parse import quote_plus

class Module(BaseModule, GithubMixin):
    meta = {
        'name': 'Github Profile Harvester',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Uses the Github API to gather user info from harvested profiles. Updates the \'contacts\' table with the results.',
        'required_keys': ['github_api'],
        'query': "SELECT DISTINCT username FROM profiles WHERE username IS NOT NULL AND resource LIKE 'Github'",
    }

    def module_run(self, usernames):
        for username in usernames:
            users = self.query_github_api(endpoint=f"/users/{quote_plus(username)}")
            # should only be one result, but loop just in case
            for user in users:
                name = user['name']
                fname, mname, lname = parse_name(name or '')
                email = user['email']
                title = 'Github Contributor'
                if user['company']:
                    title += f" at {user['company']}"
                region = user['location']
                # don't add if lacking meaningful data
                if any((fname, lname, email)):
                    self.insert_contacts(first_name=fname, middle_name=mname, last_name=lname, email=email, title=title, region=region)
