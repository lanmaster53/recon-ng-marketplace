from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'Whoxy Company DNS Lookup',
        'author': 'Ryan Hays (@_ryanhays)',
        'version': '1.1',
        'description': 'Uses the Whoxy API to query DNS records belonging to a company',
        'required_keys': ['whoxy_api'],
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
    }

    def module_run(self, companies):
        key = self.keys.get('whoxy_api')
        for company in companies:
            self.heading(company, level=0)
            cur_page = 1
            total_pages = 1

            while cur_page <= total_pages:
                resp = self.request('GET', f"http://api.whoxy.com/?key={key}&reverse=whois&company={company}&page={cur_page}")
                if resp.json().get('total_results') <= 0:
                    break

                cur_page = resp.json().get('current_page')
                total_pages = resp.json().get('total_pages')

                for domain in resp.json().get('search_result'):
                    self.insert_hosts(host=domain['domain_name'])

                cur_page += 1
