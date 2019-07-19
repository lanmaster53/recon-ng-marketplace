from recon.core.module import BaseModule
from recon.mixins.search import BingAPIMixin


class Module(BaseModule, BingAPIMixin):

    meta = {
        "name": "Bing LinkedIn Profile Contact Harvester",
        "author": "Cam Barts (@cam-barts)",
        "version": "1.0",
        "description": "Harvests Basic Contact Information from Bing based on LinkedIn profiles",
        "required_keys": ["bing_api"],
        "comments": (
            'Use Bing\'s top search results for LinkedIn urls to gather names, titles, and companies',
            'This works for profiles that are set to public on LinkedIn'
        ),
        "query": "SELECT DISTINCT url FROM profiles WHERE resource='LinkedIn'",
        "options": (),
    }

    def module_run(self, urls):
        for url in urls:
            self.get_contact_info(url)

    def get_contact_info(self, url):
        search_result = self.search_bing_api(url, 1)
        if search_result and search_result[0]["url"] == url:
            search_result = search_result[0]
            link_title = search_result["name"]
            name_and_title = link_title.split("|")[0]
            name_title_company_list = name_and_title.split("-")
            name = name_title_company_list[0].strip().split()
            if "linkedin" not in name_title_company_list[-1].lower():
                company = name_title_company_list[-1]
            else:
                company = False
            if not company:
                title = name_title_company_list[1]
            else:
                title = f"{name_title_company_list[1]} at {company}"
            if len(name) > 2:
                self.insert_contacts(
                    first_name=name[0],
                    middle_name=name[1],
                    last_name=" ".join(name[2:]),
                    title=title,
                )
            else:
                self.insert_contacts(first_name=name[0], last_name=name[1], title=title)
