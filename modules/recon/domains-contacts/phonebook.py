# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
from recon.mixins.threads import ThreadingMixin
# module specific imports
import time


class Module(BaseModule, ThreadingMixin):

    # modules are defined and configured by the "meta" class variable
    # "meta" is a dictionary that contains information about the module, ranging from basic information, to input that affects how the module functions
    # below is an example "meta" declaration that contains all of the possible definitions

    meta = {
        'name': 'Phonebook.cz email search',
        'author': 'TheToddLuci0',
        'version': '0.1',
        'description': 'Query phonebook.cz for email addresses for a given domain.',
        'dependencies': [],
        'files': [],
        'required_keys': ['intelx'],
        'comments': (),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': (
            ('api_url', 'https://2.intelx.io/', 'True',
             'Base URL. Is set by phonebook in it\'s config.js, but I have no indication it actually changes.'),
            ('limit', 10000, 'True', 'Maximum number of results ro return.')
        ),
    }

    # "name", "author", "version", and "description" are required entries
    # "dependencies" is required if the module requires the installation of a third party library (list of PyPI install names)
    # "files" is required if the module includes a reference to a data file in the "/data" folder of the marketplace repository
    # "required_keys" is required if the module leverages an API or builtin functionality that requires a key
    # "query" is optional and determines the "default" source of input
    # the "SOURCE" option is only available if "query" is defined
    # "options" expects a tuple of tuples containing 4 elements:
    # 1. the name of the option
    # 2. the default value of the option (strings, integers and boolean values are allowed)
    # 3. a boolean value (True or False) for whether or not the option is mandatory
    # 4. a description of the option
    # "comments" are completely optional

    # optional method
    # def module_pre(self):
    # override this method to execute code prior to calling the "module_run" method
    # returned values are passed to the "module_run" method and must be captured in a parameter
    # return value

    # mandatory method
    # the second parameter is required to capture the result of the "SOURCE" option, which means that it is only required if "query" is defined within "meta"
    # the third parameter is required if a value is returned from the "module_pre" method
    def module_run(self, domains):
        # do something leveraging the api methods discussed below
        # local option values can be accessed via self.options['name'] or self.options.get('name')
        # key values can be accessed via self.keys['name'] or self.keys.get('name')
        # use the "self.workspace" class property to access the workspace location
        # threading can be used anywhere with the module through the usage of the "self.thread" api call
        # the "self.thread" api call requires a "module_thread" method which acts as the worker for each item in a queue
        self.API_KEY = self.keys.get('intelx')
        self.API_ROOT = self.options.get('API_URL')
        if self.API_ROOT[-1] == '/':
            self.API_ROOT = self.API_ROOT[:-1]
        self.debug(self.API_ROOT)
        limit = self.options.get('limit')

        # "self.thread" takes at least one argument
        # the first argument must be an iterable that contains all of the items to fill the queue
        # all other arguments get blindly passed to the "module_thread" method where they can be accessed at the thread level
        self.thread(domains, limit)

    # optional method
    # the first received parameter is required to capture an item from the queue
    # all other parameters passed in to "self.thread" must be accounted for

    def module_thread(self, domain, limit):
        # never catch KeyboardInterrupt exceptions in the "module_thread" method as threads don't see them
        # do something leveraging the api methods discussed below

        phonebook_res = self.phonebooksearch(domain, limit)
        for i in phonebook_res:
            for data in i['selectors']:
                if data['selectortype'] == 1:
                    self.insert_contacts(email=data['selectorvalue'])
                else:
                    self.verbose("I don't know what to do with this")
                    self.verbose(data)

    # Everything from here on is (based on) stolen code from the IntelX API SDK
    # https://github.com/IntelligenceX/SDK/blob/master/Python/intelxapi.py

    def phonebooksearch(self, term, maxresults=10000, buckets=[], timeout=5, datefrom="", dateto="", sort=4, media=0, terminate=[], target=2):
        """
        Conduct a phonebook search based on a search term.
        Other arguments have default values set, however they can be overridden to complete an advanced search.
        """
        results = []
        done = False
        search_id = self.PHONEBOOK_SEARCH(
            term, maxresults, buckets, timeout, datefrom, dateto, sort, media, terminate, target)
        if (len(str(search_id)) <= 3):
            self.error(
                f"intelx.PHONEBOOK_SEARCH() Received {self.get_error(search_id)}")
        while done == False:
            # lets give the backend a chance to aggregate our data
            time.sleep(1)
            r = self.query_pb_results(search_id, maxresults)
            results.append(r)
            maxresults -= len(r['selectors'])
            if (r['status'] == 1 or r['status'] == 2 or maxresults <= 0):
                if (maxresults <= 0):
                    self.INTEL_TERMINATE_SEARCH(search_id)
                done = True
        return results

    def INTEL_TERMINATE_SEARCH(self, uuid):
        """
        Terminate a previously initialized search based on its UUID.
        """
        h = {'x-key': self.API_KEY}
        r = self.request('GET', self.API_ROOT +
                         f'/intelligent/search/terminate?id={uuid}', headers=h)
        if (r.status_code == 200):
            return True
        else:
            return r.status_code

    def PHONEBOOK_SEARCH(self, term, maxresults=100, buckets=[], timeout=5, datefrom="", dateto="", sort=4, media=0, terminate=[], target=0):
        """
        Initialize a phonebook search and return the ID of the task/search for further processing
        """
        h = {'x-key': self.API_KEY}
        p = {
            "term": term,
            "buckets": buckets,
            "lookuplevel": 0,
            "maxresults": maxresults,
            "timeout": timeout,
            "datefrom": datefrom,
            "dateto": dateto,
            "sort": sort,
            "media": media,
            "terminate": terminate,
            "target": target
        }
        r = self.request('POST', self.API_ROOT +
                         '/phonebook/search', headers=h, json=p)
        if r.status_code == 200:
            return r.json()['id']
        else:
            return r.status_code

    def PHONEBOOK_SEARCH_RESULT(self, id, limit=1000, offset=-1):
        """
        Fetch results from a phonebook search based on ID.
        offset:
        - Do not use. If omitted (default), each call will get the next available results.
        ___________________________________________
        RETURN VALUES
        status (results status):
        - 0: Sucess with results.
        - 1: No more results available.
        - 2: Search ID not found.
        - 3: No results yet, but keep trying.
        """
        h = {'x-key': self.API_KEY}
        r = self.request('GET', self.API_ROOT +
                         f'/phonebook/search/result?id={id}&limit={limit}&offset={offset}', headers=h)
        if (r.status_code == 200):
            return r.json()
        else:
            return r.status_code

    def query_pb_results(self, id, limit):
        """
        Query the results fom a phonebook search.
        Meant for usage within loops.
        """
        results = self.PHONEBOOK_SEARCH_RESULT(id, limit)
        return results

    def get_error(self, code):
        """
        Get error string by respective HTTP response code.
        """
        if code == 200:
            return "200 | Success"
        if code == 204:
            return "204 | No Content"
        if code == 400:
            return "400 | Bad Request"
        if code == 401:
            return "401 | Unauthorized"
        if code == 402:
            return "402 | Payment required."
        if code == 404:
            return "404 | Not Found"
