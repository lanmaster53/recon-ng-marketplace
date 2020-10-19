from recon.core.module import BaseModule
from datetime import datetime
import re
import time

class Module(BaseModule):

    meta = {
        'name': 'XSSed Domain Lookup',
        'author': 'Micah Hoffman (@WebBreacher)',
        'version': '1.1',
        'description': 'Checks XSSed.com for XSS records associated with a domain and displays the first 20 results.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }
   
    def module_run(self, domains):
        url = 'http://xssed.com/search?key=%s'
        url_vuln = 'http://xssed.com/mirror/%s/'
        for domain in domains:
            self.heading(domain, level=0)
            resp = self.request('GET', url % domain)
            vulns = re.findall('mirror/([0-9]+)/\' target=\'_blank\'>', resp.text)
            for vuln in vulns:
                # Go fetch and parse the specific page for this item
                resp_vuln = self.request('GET', url_vuln % vuln)
                # Parse the response and get the details
                details = re.findall(r'<th class="row3"[^>]*>[^:?]+[:?]+(.+?)<\/th>', resp_vuln.text)#.replace('&nbsp;', ' '))
                details = [self.html_unescape(x).strip() for x in details]
                if not re.match(rf"(^|.*\.){re.escape(domain)}$", details[5], re.IGNORECASE):
                    continue
                data = {}
                data['host'] = details[5]
                data['reference'] = url_vuln % vuln
                data['publish_date'] = datetime.strptime(details[1], '%d/%m/%Y')
                data['category'] = details[6]
                data['status'] = re.search(r'([UNFIXED]+)',details[3]).group(1).lower()
                data['example'] = details[8]
                self.insert_vulnerabilities(**data)
                # results in 503 errors if not throttled
                time.sleep(1)
            if not vulns:
                self.output('No vulnerabilites found.')
