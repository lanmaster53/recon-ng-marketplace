from recon.core.module import BaseModule
from recon.mixins.search import BingAPIMixin
from recon.utils.parsers import parse_name
import re


class Module(BaseModule, BingAPIMixin):

    meta = {
        "name": "Bing LinkedIn Profile Contact Harvester",
        "author": "Cam Barts (@cam-barts)",
        "version": "1.2",
        "description": "Harvests Basic Contact Information from Bing based on LinkedIn profiles.",
        "required_keys": ["bing_api"],
        "comments": (
            "Use Bing's top search results for LinkedIn urls to gather names, titles, and companies",
            "This works for profiles that are set to public on LinkedIn",
        ),
        "query": "SELECT DISTINCT url FROM profiles WHERE resource='LinkedIn'",
        "options": (),
    }

    def module_run(self, urls):
        for url in urls:
            self.get_contact_info(url)

    def get_contact_info(self, url):
        search_result = self.search_bing_api(url, 1)

        # Search by url. If the url doesn't match, it has potential to be a different person
        if search_result and search_result[0]["url"] == url:
            search_result = search_result[0]
            # "Name" is a misnomer, it actually refers to the link title
            link_title = search_result["name"]

            # Split the title on the pipe to get rid of "linkedIn" portion at the end
            name_and_title = link_title.split("|")[0]
            # Split whats left on the Dashes, which is usually name - title - company
            # some european LinkedIn sites use em-dash
            EM_DASH = b'\xe2\x80\x93'.decode('utf-8')
            delimeter_expression = '- | ' + EM_DASH
            name_title_company_list = re.split(delimeter_expression, name_and_title)
            # Parse out name
            fullname = name_title_company_list[0]
            fname, mname, lname = parse_name(fullname)

            # Sometimes "LinkedIn" is left at the end anyway, and we don't want to confuse that for the company
            if "linkedin" not in name_title_company_list[-1].lower():
                company = name_title_company_list[-1]
            else:
                company = False

            # Try to parse out a title and company if it's there
            if "linkedin" not in name_title_company_list[1].lower():
                if not company:
                    title = name_title_company_list[1]
                else:
                    title = f"{name_title_company_list[1]} at {company}"
                self.insert_contacts(
                    first_name=fname, middle_name=mname, last_name=lname, title=title
                )
            else:
                self.insert_contacts(
                    first_name=fname, middle_name=mname, last_name=lname
                )
