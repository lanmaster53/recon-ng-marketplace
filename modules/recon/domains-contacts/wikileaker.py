# module specific imports
import re
import time

import lxml.html
from recon.core.module import BaseModule


class Module(BaseModule):

    meta = {
        'name': 'WikiLeaker',
        'author': 'Joe Gray (@C_3PJoe)',
        'version': '1.0',
        'description': 'A WikiLeaks scraper inspired by the Datasploit module previously written in Python2. It '
                       'searches Wikileaks for leaks containing the subject domain. If anything is found, this module '
                       'will seek to parse out the URL, Sender Email, Date, Leak, and Subject of the email. This will '
                       'update the \'Contacts\' table with the results.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
    }

    def module_run(self, domains):
        for domain in domains:
            page_count = 1
            while True:
                URL = 'https://search.wikileaks.org/?query=&exact_phrase=' + domain + \
                      '&include_external_sources=True&order_by=newest_document_date&page=' + str(page_count)
                self.verbose(URL)
                resp = self.request('GET', URL)
                time.sleep(1)
                if resp.status_code != 200:
                    self.alert('An error occurred: ' + str(resp.status_code))
                    break
                else:
                    root = lxml.html.fromstring(resp.text)
                    search_data = root.xpath('//div[@class="result"]')

                    if len(search_data) > 0:
                        for i in search_data:
                            link = i.xpath("concat(div/h4/a[contains(@href, '/emails/emailid/')]/@href, '')").strip()

                            if link:
                                subject = i.xpath("concat(div/h4/a, '')").strip()
                                leak = i.xpath("concat(div/div[@class='leak-label'], '')").strip()
                                created = i.xpath("concat(div/div[@class='dates']/div[@class='date' and "
                                                  "contains(text(), 'Created')]/span, '')").strip()
                                excerpt = i.xpath("concat(div[@class='info']/div[@class='excerpt'], '')").strip()

                                emails = re.findall("email:\\xa0([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
                                                    excerpt)

                                for email in emails:
                                    self.alert(f'Leak: {leak}')
                                    self.output(f'URL: {link}')
                                    self.verbose(f'Date: {created}')
                                    self.verbose(f'Sender: {email.strip()}')
                                    self.verbose(f'Subject: {subject}')
                                    self.insert_contacts(email=email.strip(), notes=link)
                    else:
                        break

                page_count += 1
