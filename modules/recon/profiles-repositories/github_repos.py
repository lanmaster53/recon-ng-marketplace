from recon.core.module import BaseModule
from recon.mixins.github import GithubMixin
from urllib.parse import quote_plus

class Module(BaseModule, GithubMixin):
    meta = {
        'name': 'Github Code Enumerator',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.1',
        'description': 'Uses the Github API to enumerate repositories and gists owned by a Github user. Updates the \'repositories\' table with the results.',
        'required_keys': ['github_api'],
        'query': "SELECT DISTINCT username FROM profiles WHERE username IS NOT NULL AND resource LIKE 'Github'",
        'options': (
            ('ignoreforks', False, False, 'ignore forks'),
        ),
    }

    def module_run(self, users):
        for user in users:
            self.heading(user, level=0)
            # enumerate repositories
            repos = self.query_github_api(f"/users/{quote_plus(user)}/repos")
            for repo in repos:
                if self.options['ignoreforks'] and repo['fork']:
                    continue
                data = {
                    'name': repo['name'],
                    'owner': repo['owner']['login'],
                    'description': repo['description'],
                    'url': repo['html_url'],
                    'resource': 'Github',
                    'category': 'repo',
                }
                self.insert_repositories(**data)
            # enumerate gists
            gists = self.query_github_api(f"/users/{quote_plus(user)}/gists")
            for gist in gists:
                files = gist['files'].values()
                for _file in files:
                    data = {
                        'name': _file['filename'],
                        'owner': gist['owner']['login'],
                        'description': gist['description'],
                        'url': _file['raw_url'],
                        'resource': 'Github',
                        'category': 'gist',
                    }
                    self.insert_repositories(**data)
