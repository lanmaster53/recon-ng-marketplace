from recon.core.module import BaseModule
from lxml.etree import fromstring
from urllib.parse import quote_plus
import ipaddress


class Module(BaseModule):

    meta = {
        'name': 'Whois Data Miner (ripe.net)',
        'author': 'Andrey Zhukov from USSC',
        'version': '1.0',
        'description': 'Uses the RIPE Whois to harvest companies, locations, netblocks, and contacts associated with the given company search string. Updates the respective tables with the results.',
        'dependencies': ['lxml'],
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
    }

    def module_run(self, searches):
        for search in searches:
            url = 'http://rest.db.ripe.net/search?source=ripe&query-string=%s' % (quote_plus(search))
            response = self.request('GET', url)
            if response.status_code != 200:
                continue
            for _object in fromstring(response.content).xpath('//objects/object'):
                _type = _object.xpath('@type')[0]
                if _type == 'inetnum':
                    try:
                        inetnum = [x.strip() for x in _object.xpath("//attributes/attribute[@name='inetnum']/@value")[0].split('-')]
                        netname = _object.xpath("//attributes/attribute[@name='netname']/@value")[0]
                        start = ipaddress.ip_address(inetnum[0])
                        end = ipaddress.ip_address(inetnum[1])
                        blocks = ipaddress.summarize_address_range(start, end)
                    except ValueError:
                        self.error('IPv6 ranges not supported: %s-%s' % (net['@startAddress'], net['@endAddress']))
                        continue
                    for block in blocks:
                        self.insert_netblocks(netblock=str(block), notes=netname)

                elif _type == 'role':
                    pass

                elif _type == 'person':
                    try:
                        person = _object.xpath("//attributes/attribute[@name='person']/@value")[0]
                        self.insert_contacts(first_name=person.split()[0], last_name=person.split()[1])
                        address = _object.xpath("//attributes/attribute[@name='address']/@value")[0]
                        self.insert_locations(street_address=address)
                    except Exception as e:
                        self.error(str(e))

                elif _type == 'organisation':
                    try:
                        organisation = _object.xpath("//attributes/attribute[@name='org-name']/@value")[0]
                        self.insert_companies(company=organisation)
                        address = _object.xpath("//attributes/attribute[@name='address']/@value")[0]
                        self.insert_locations(street_address=address)
                    except Exception as e:
                        self.error(str(e))
