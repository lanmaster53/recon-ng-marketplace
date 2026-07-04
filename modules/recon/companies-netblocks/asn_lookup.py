from recon.core.module import BaseModule
import re


class Module(BaseModule):

    meta = {
        'name': 'ASN Lookup',
        'author': 'Nicholas Curran (@ncurran)',
        'version': '1.0',
        'description': (
            'Searches for Autonomous System Numbers associated with each company '
            'and inserts all announced IP prefixes into the netblocks table. '
            'Uses the HackerTarget ASN lookup API.'
        ),
        'comments': (
            'Free tier: 50 requests/day without a key.',
            'Set the hackertarget_api key to raise the rate limit.',
            'Results are filtered to ASNs whose name contains at least one '
            'significant word (4+ chars) from the company name.',
        ),
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
    }

    def module_run(self, companies):
        for company in companies:
            self.heading(company, level=0)

            # Build list of significant words from the company name for matching.
            # Skip short tokens (Inc, LLC, Ltd, Co, etc.) to avoid false positives.
            search_words = [w.lower() for w in re.split(r'\W+', company) if len(w) >= 4]
            if not search_words:
                self.error(f"Company name '{company}' too short to search reliably.")
                continue

            params = {'q': company}
            api_key = self.get_key('hackertarget_api')
            if api_key:
                params['apikey'] = api_key

            resp = self.request('GET', 'https://api.hackertarget.com/aslookup/', params=params)

            if resp.status_code == 429:
                self.error('Rate limit reached. Set the hackertarget_api key or retry later.')
                break
            if resp.status_code != 200:
                self.error(f"Unexpected response ({resp.status_code}) for '{company}'.")
                continue
            if 'API count exceeded' in resp.text:
                self.error('Daily API quota exceeded. Set the hackertarget_api key or retry tomorrow.')
                break
            if resp.text.startswith('error'):
                self.output(f"No ASNs found for '{company}'.")
                continue

            # Parse "ASNNUM","NAME, COUNTRY" lines
            matched_asns = []
            for line in resp.text.strip().splitlines():
                m = re.match(r'"(\d+)","(.+)"', line.strip())
                if not m:
                    continue
                asn_num, asn_name = m.group(1), m.group(2)
                if any(word in asn_name.lower() for word in search_words):
                    matched_asns.append((asn_num, asn_name))

            if not matched_asns:
                self.output(f"No ASNs matched '{company}' in search results.")
                continue

            for asn_num, asn_name in matched_asns:
                self.verbose(f"Fetching prefixes for AS{asn_num} ({asn_name})")

                params = {'q': f'AS{asn_num}'}
                if api_key:
                    params['apikey'] = api_key

                resp = self.request('GET', 'https://api.hackertarget.com/aslookup/', params=params)

                if resp.status_code == 429:
                    self.error('Rate limit reached. Set the hackertarget_api key or retry later.')
                    return
                if 'API count exceeded' in resp.text:
                    self.error('Daily API quota exceeded. Set the hackertarget_api key or retry tomorrow.')
                    return
                if resp.status_code != 200 or resp.text.startswith('error'):
                    self.error(f"Failed to retrieve prefixes for AS{asn_num}.")
                    continue

                lines = resp.text.strip().splitlines()
                # First line is the ASN descriptor, remainder are CIDR prefixes
                prefixes = [l.strip() for l in lines[1:] if '/' in l]
                for prefix in prefixes:
                    self.insert_netblocks(netblock=prefix)
                self.output(f"AS{asn_num} ({asn_name}): {len(prefixes)} prefixes inserted.")
