from recon.core.module import BaseModule
from recon.mixins.github import GithubMixin
from urllib.parse import quote_plus

class Module(BaseModule, GithubMixin):
    meta = {
        'name': 'Github Resource Miner',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.1',
        'description': 'Uses the Github API to enumerate repositories and member profiles associated with a company search string. Updates the respective tables with the results.',
        'required_keys': ['github_api'],
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
        'options': (
            ('ignoreforks', True, True, 'ignore forks'),
        ),
    }

    def module_run(self, companies):
        for company in companies:
            self.heading(company, level=0)
            # enumerate members
            members = self.query_github_api(f"/orgs/{quote_plus(company)}/members")
            for member in members:
                data = {
                    'username': member['login'],
                    'url': member['html_url'],
                    'notes': company,
                    'resource': 'Github',
                    'category': 'coding',
                }
                self.insert_profiles(**data)
            # enumerate repositories
            repos = self.query_github_api(f"/orgs/{quote_plus(company)}/repos")
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
