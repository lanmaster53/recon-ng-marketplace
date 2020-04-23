from recon.core.module import BaseModule
import os
import re
from ipwhois import IPWhois


class Module(BaseModule):

    meta = {
        'name': 'Hosts to Netblocks Migrator',
        'author': 'Andrey Zhukov from USSC',
        'version': '1.0',
        'description': 'Finding subnets through Whois relying on IP addresses from \'hosts\' table. Updates \'netblocks\', \'locations\', \'contacts\' and \'hosts\' tables.',
        'dependencies': ['ipwhois'],
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
    }

    def module_run(self, ip_addresses):
        netblocks = set()
        addresses = set()
        emails = set()
        cidr_ranges = []
        geo = {}
        ips = []
        for ip in ip_addresses:
            if ip not in cidr_ranges:
                try:
                    lookup = IPWhois(ip).lookup_whois()
                    for net in lookup['nets']:
                        descr = net['name'] or '; '.join(str(net['description']).split('\n'))
                        cidrs = map(lambda x: x.strip(), net['cidr'].split(','))
                        for cidr in cidrs:
                            netblocks.add((cidr, descr))
                            cidr_ranges.extend(self.cidr_to_list(cidr))
                            if net['city'] != None or net['country'] != None:
                                geo[cidr] = (net['city'], net['country'])
                            ips.append(ip)
                            self.output('%s %s (%s)' % (cidr, descr, ip))
                        if net['address']:
                            address = '; '.join(net['address'].split('\n'))
                            addresses.add(address)
                            self.output(address)
                        if net['emails']:
                            for email in net['emails']:
                                emails.add(email)
                                self.output(email)
                except Exception as e:
                    self.error(str(e))
        for netblock, descr in netblocks:
            self.insert_netblocks(netblock=netblock, notes=descr)
        for address in addresses:
            self.insert_locations(street_address=address)
        for email in emails:
            self.insert_contacts(email=email)
        for cidr in geo:
            for ip in ips:
                if ip in self.cidr_to_list(cidr):
                    region, country = self.query('SELECT region, country FROM hosts WHERE ip_address=?', (ip, ))[0]
                    if not region:
                        region = geo[cidr][0]
                    if not country:
                        country = geo[cidr][1]
                    self.query('UPDATE hosts SET region=?, country=? WHERE ip_address=?', (region, country, ip))
