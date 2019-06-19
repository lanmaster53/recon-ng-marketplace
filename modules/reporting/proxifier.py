from recon.core.module import BaseModule
from recon.mixins.threads import ThreadingMixin

class Module(BaseModule, ThreadingMixin):

    meta = {
        'name': 'Proxifier',
        'author': 'AverageSecurityGuy (@averagesecguy)',
        'version': '1.0',
        'description': 'Requests URLs from the database for the purpose of populating an inline proxy. Requires that the global proxy option be set prior to running the module.',
        'query': 'SELECT example FROM vulnerabilities WHERE category=\'Google Dork\'',
    }

    def module_run(self, urls):
        self.thread(urls)

    def module_thread(self, url):
        try:
            resp = self.request('GET', url)
            self.verbose(f"{url} => {resp.status_code}")
        except Exception as e:
            self.error(f"{url} => {e}")
