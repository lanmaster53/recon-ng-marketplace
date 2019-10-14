from recon.core.module import BaseModule

from recon.mixins.threads import ThreadingMixin

from bs4 import BeautifulSoup


class Module(BaseModule, ThreadingMixin):

    meta = {
        "name": "Advance Background Check Lookup",
        "author": "Cam Barts (@cam-barts)",
        "version": "1.0",
        "description": "Checks names at advancedbackgroundchecks.com.",
        "dependencies": ["beautifulsoup4"],
        "comments": ("Inspiration drawn from @xillwillx skiptracer module https://github.com/xillwillx/skiptracer/blob/master/plugins/advance_background_checks.py"),
        "query": "SELECT DISTINCT first_name, last_name, region FROM contacts WHERE first_name IS NOT NULL AND last_name IS NOT NULL",
        "options": (
            ("location", "", True, "location to search (city, state, or zip)"),
        ),
    }

    def module_run(self, people):
        url_names = []
        for person in people:
            name = f"{person[0]}-{person[1]}"
            if person[2]:
                region = f"{person[2]}".replace(" ", "-")
            else:
                region = self.options["location"]
            url = f"https://www.advancedbackgroundchecks.com/name/{name}_{region}"
            url_names.append((url, name))
        self.thread(url_names)

    def module_thread(self, url_name):
        url = url_name[0]
        name = url_name[1].replace("-", " ")

        resp = self.request("GET", url)
        soup = BeautifulSoup(resp.content, features="html.parser")

        # Output number of results for person
        num_results = soup.find("h1", attrs={"class": "list-results-header"}).text
        clean_num_results = " ".join(num_results.split())
        self.alert(clean_num_results)

        # If only one result, go to that persons page any grab goodies
        if int(clean_num_results.split()[0]) > 1:
            self.alert(f"Too many results for {name}, try to narrow your search")
            self.alert(url)
            return
        elif int(clean_num_results.split()[0]) == 0:
            self.alert(f"No results for {name}")
            return
        else:
            link = soup.find("a", attrs={"class": "link-to-details"})
            new_url = f"https://www.advancedbackgroundchecks.com{link['href']}"
            person_resp = self.request("GET", new_url)
            person_soup = BeautifulSoup(person_resp.content, features="html.parser")

            # Grab current address
            current_address_tag = person_soup.find("p", attrs={"class": "address-link"})
            current_address = " ".join(
                current_address_tag.text.split()[1:]
            )  # The first word is "map", so skip that

            self.insert_locations(street_address=current_address)

            # Grab emails
            emails_tag = person_soup.find("div", attrs={"class": "detail-box-email"})
            emails = list(emails_tag.stripped_strings)

            # Add contacts
            for email in emails:
                self.insert_contacts(
                    first_name=name.split()[0],
                    last_name=name.split()[1],
                    region=current_address,
                    email=email,
                    country="United States",
                )

            # Update regions
            self.query(
                "UPDATE contacts SET region = ? WHERE first_name = ? AND last_name = ?",
                (current_address, name.split()[0], name.split()[1]),
            )
