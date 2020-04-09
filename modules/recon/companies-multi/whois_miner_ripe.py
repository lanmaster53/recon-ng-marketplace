from recon.core.module import BaseModule
from recon.utils import netblock
from lxml.etree import fromstring
from urllib.parse import quote_plus

class Module(BaseModule):

    meta = {
        'name': 'Whois Data Miner (ripe.net)',
        'author': 'Andrey Zhukov from USSC',
        'version': '1.0',
        'description': 'Uses the RIPE Whois to harvest companies, locations, netblocks, and contacts associated with the given company search string. Updates the respective tables with the results.',
        'dependencies': ['lxml'],
        'comments': (
            'Validate results of the SEARCH string with these URLs:',
            '\thttp://rest.db.ripe.net/search?source=ripe&query-string=<SEARCH>',
        ),
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
    }

    def module_run(self, searches):
        for search in searches:
            url = 'http://rest.db.ripe.net/search?source=ripe&query-string=%s' % (quote_plus(search))
            response = self.request(url)
            if response.status_code != 200:
                continue

            for _object in fromstring(response.text).xpath('//objects/object'):
                _type = _object.xpath('@type')[0]
                if _type == 'inetnum':
                    try:
                        inetnum = [ x.strip() for x in _object.xpath("//attributes/attribute[@name='inetnum']/@value")[0].split('-') ]
                        begin = netblock.strtoip( inetnum[0] )
                        end = netblock.strtoip( inetnum[1] )
                        blocks = netblock.lhcidrs(begin, end)
                    except ValueError:
                        self.alert('IPv6 ranges not supported: %s-%s' % (net['@startAddress'], net['@endAddress']))
                        continue
                    for block in blocks:
                        ip = netblock.iptostr(block[0])
                        cidr = '%s/%s' % (ip, str(block[1]))
                        self.add_netblocks(netblock=cidr)

                elif _type == 'role':
                    pass

                elif _type == 'person':
                    try:
                        person = _object.xpath("//attributes/attribute[@name='person']/@value")[0]
                        self.add_contacts( first_name=person.split()[0], last_name=person.split()[1] )
                        address = _object.xpath("//attributes/attribute[@name='address']/@value")[0]
                        self.add_locations(street_address=address)
                    except Exception as e:
                        self.alert( str(e) )

                elif _type == 'organisation':
                    try:
                        organisation = _object.xpath("//attributes/attribute[@name='org-name']/@value")[0]
                        self.add_companies(company=organisation)
                        address = _object.xpath("//attributes/attribute[@name='address']/@value")[0]
                        self.add_locations(street_address=address)
                    except Exception as e:
                        self.alert( str(e) )
