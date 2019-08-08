from recon.core.module import BaseModule
from lxml.html import fromstring
from urllib.parse import quote_plus

class Module(BaseModule):

	meta = {
		'name': 'viewdns.info reverse whois domain harvester',
		'author': 'Gaetan Ferry (@_mabote_) from @synacktiv',
		'version': '1.0',
		'description': 'Harvests domain names belonging to a company by using '
					+  'the viewdns.info free reverse whois tool.',
		'comments': ("Does not support company names < 6 characters",),
		'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
	}

	def module_run(self, companies):
		base_url = "http://viewdns.info/reversewhois/"
		for company in companies:
			self.heading(company, level=0)
			url = base_url + "?q=" + quote_plus(company)
			resp = self.request("GET", url)
			if resp.status_code != 200:
				self.alert('An error occured: ' + str(resp.status_code))
				continue
			content = fromstring(resp.text)
			domains = content.xpath("//table[@border='1']//tr/td[1]//text()")
			# remove table headers
			if len(domains) <= 0:
				continue

			domains = domains[1::]
			for domain in domains:
				self.insert_domains(domain)


