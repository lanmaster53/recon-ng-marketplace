from recon.core.module import BaseModule
import os
import re
from ipwhois import IPWhois

class Module(BaseModule):

    meta = {
        'name': 'Hosts to Netblock Migrator',
        'Author': 'Andrey Zhukov from USSC',
        'description': 'Finding subnets through Whois relying on IP addresses from \'table\' table',
        'comments': (
            '',
        ),
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
    }

    def module_run(self, ip_addresses):
        netblocks = set()
        cidr_ranges = []
        for ip in ip_addresses:
            if not ip in cidr_ranges:
                try:
                    lookup = IPWhois( ip ).lookup_whois()
                    for net in lookup['nets']:
                        descr = net['name'] or ';'.join( str( net['description'] ).split('\n') )
                        cidrs = map( lambda x:x.strip(), net['cidr'].split(',') )
                        for cidr in cidrs:
                            netblocks.add( (cidr,descr) )
                            cidr_ranges.extend( self.cidr_to_list(cidr) )
                            self.output( '%s %s (%s)' % (cidr,descr,ip) )
                except Exception as e:
                    self.error( str(e) )
        for netblock,descr in netblocks:
            self.insert_netblocks( netblock=netblock, notes=descr )
