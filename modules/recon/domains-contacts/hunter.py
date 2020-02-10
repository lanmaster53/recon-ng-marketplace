from recon.core.module import BaseModule
from recon.core.framework import FrameworkException

class Module(BaseModule):
    meta = {
        "name": "Hunter.io Domain",
        "author": "aplneto",
        "version": "1.0",
        "description": "Uses hunter.io to find e-mails from given domains",
        "dependencies": [],
        "files": [],
        "required_keys": ['hunter_io'],
        "query":"SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL"
    }
    
    def module_run(self, domains):
        self.__key = self.keys['hunter_io']

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
                "GET", self.__uri, params=baseparams
            )


            information = response.json()

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
            self.insert_contacts(**contact)