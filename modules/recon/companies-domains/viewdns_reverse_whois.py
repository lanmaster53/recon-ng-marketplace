from recon.core.module import BaseModule
from lxml.html import fromstring


class Module(BaseModule):

    meta = {
        'name': 'Viewdns Reverse Whois Domain Harvester',
        'author': 'Gaetan Ferry (@_mabote_) from @synacktiv',
        'version': '1.1',
        'description': 'Harvests domain names belonging to a company by using '
            + 'the viewdns.info free reverse whois tool.',
        'comments': (
            'Does not support company names < 6 characters',
        ),
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
    }

    def module_run(self, companies):
        url = 'https://viewdns.info/reversewhois/'
        for company in companies:
            self.heading(company, level=0)
            if len(company) < 6:
                self.alert('Company name too short, skipping')
                continue
            payload = {'q': company}
            resp = self.request('GET', url, params=payload)
            if resp.status_code != 200:
                self.alert('An error occured: ' + str(resp.status_code))
                continue
            content = fromstring(resp.text)
            domains = content.xpath("//table[@border='1']//tr/td[1]//text()")
            if len(domains) <= 0:
                continue
            # remove table headers
            domains = domains[1::]
            for domain in domains:
                self.insert_domains(domain)
