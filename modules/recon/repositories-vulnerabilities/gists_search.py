from recon.core.module import BaseModule
import os

class Module(BaseModule):
    meta = {
        'name': 'Github Gist Searcher',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Uses the Github API to download and search Gists for possible information disclosures. Updates the \'vulnerabilities\' table with the results.',
        'comments': (
            'Gist searches are case sensitive. Include all desired permutations in the keyword list.',
        ),
        'query': "SELECT DISTINCT url FROM repositories WHERE url IS NOT NULL AND resource LIKE 'Github' AND category LIKE 'gist'",
        'options': (
            ('keywords', os.path.join(BaseModule.data_path, 'gist_keywords.txt'), True, 'file containing a list of keywords'),
        ),
        'files': ['gist_keywords.txt'],
    }

    def module_run(self, gists):
        with open(self.options['keywords']) as fp:
            # create list of keywords and filter out comments
            keywords = [x.strip() for x in fp.read().splitlines() if x and not x.startswith('#')]
        for gist in gists:
            filename = gist.split(os.sep)[-1]
            self.heading(filename, level=0)
            resp = self.request('GET', gist)
            for keyword in keywords:
                self.verbose(f"Searching Gist for: {keyword}")
                lines = resp.text.splitlines()
                for lineno, line in enumerate(lines):
                    if keyword in line:
                        data = {
                            'reference': gist,
                            'example': f"line {lineno}: {line.strip()}",
                            'category': 'Information Disclosure',
                        }
                        self.insert_vulnerabilities(**data)
