from recon.core.module import BaseModule
from recon.core.framework import FrameworkException

class Module(BaseModule):
    meta = {
        "name": "Hunter.io Domain",
        "author": "super choque",
        "version": "0.1",
        "description": "Uses hunter.io to catch e-mails from a domain",
        "dependencies": [],
        "files": [],
        "required_keys": ['hunterio_api'],
        "query":"SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL"
    }

    def __init__(self, params, query=None):
        BaseModule.__init__(self, params, query=query)

        self.__key = None
        self.__uri = ""
    
    def module_run(self, domains):
        self.__key = self.keys['hunterio_api']

        if self.__key is None:
            self.alert("No api key detect, using trial mode instead")
            self.__uri = "https://api.hunter.io/trial/v2/domain-search"
        else:
            self.__uri = "https://api.hunter.io/v2/domain-search"
        
        for domain in domains:
            self.__search_domain(domain)

    def __search_domain(self, domain):
        self.output(
            "domain: {}".format(domain)
        )

        offset = 0
        results = 0
        first_query = True

        while (offset < results) or first_query:
            baseparams = {
                "domain": domain,
                "api_key": self.__key,
                "limit": 100,
                "offset": offset
            }

            response = self.request(
                self.__uri, method="GET", payload=baseparams
            )

            information = response.json

            if response.status_code != 200:
                self.error(
                    "Something went wrong!\n"+
                    "status code {} for domain \"{}\"".format(
                        response.status_code, domain                    
                    )
                )
                self.debug(information)
                return
            else:
                results = information['meta']['results']

                self.process_data(information['data'])

                offset += 100

            if first_query: first_query = False

        self.verbose("{} people found for {}".format(results, domain))
    
    def process_data(self, data):
        country = data['country']
        region = data['state']
        
        for registry in data['emails']:
            contact = {
                "first_name": registry["first_name"],
                "last_name": registry["last_name"],
                "email": registry["value"],
                "country": country,
                "region": region,
                "title": "Hunter.io Contact"
            }
            self.add_contacts(**contact)
            
            if registry["linkedin"] is not None:
                self.add_profiles(username=registry["linkedin"],
                category="linkedin")
            if registry["twitter"] is not None:
                self.add_profiles(username=registry["twitter"],
                category="twitter")
            if registry["phone_number"] is not None:
                self.add_profiles(resource=registry["phone_number"],
                category="phone_number")