from recon.core.module import BaseModule
from recon.core.framework import FrameworkException


class Module(BaseModule):

    meta = {
        "name": "Hunter.io Email Address Harvester",
        "author": "Super Choque (@aplneto)",
        "version": "1.3",
        "description": "Uses Hunter.io to find email addresses for given domains.",
        "dependencies": [],
        "files": [],
        "required_keys": ['hunter_io'],
        "query": "SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL",
        'options': (
            ('count', 10, True, 'Limit the amount of results returned. (10 = Free Account)'),
        )
    }

    def module_run(self, domains):
        self.__key = self.keys['hunter_io']

        if self.__key is None:
            self.alert("No API key detected, using trial mode instead")
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
                "limit": self.options['count'],
                "offset": offset
            }

            response = self.request(
                "GET", self.__uri, params=baseparams
            )

            information = response.json()

            if response.status_code != 200:
                self.error(
                    "Something went wrong!\n" +
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

            if first_query:
                first_query = False

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
                "region": region
            }
            self.insert_contacts(**contact)
