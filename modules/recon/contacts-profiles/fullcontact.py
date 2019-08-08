from recon.core.module import BaseModule
from recon.utils.parsers import parse_name
from time import sleep


def find(key, dictionary):
    for k, v in dictionary.items():
        if k == key:
            yield v
        elif isinstance(v, dict):
            for result in find(key, v):
                yield result
        elif isinstance(v, list):
            for d in v:
                for result in find(key, d):
                    yield result


class Module(BaseModule):

    meta = {
        'name': 'FullContact Contact Enumerator',
        'author': 'Tim Tomes (@lanmaster53) and Cam Barts (@cam-barts)',
        'version': '1.1',
        'description': 'Harvests contact information and profiles from the fullcontact.com API using email addresses '
                       'as input. Updates the \'contacts\' and \'profiles\' tables with the results.',
        'required_keys': ['fullcontact_api'],
        'query': 'SELECT DISTINCT email FROM contacts WHERE email IS NOT NULL',
    }

    def module_run(self, entities):
        api_key = self.keys.get('fullcontact_api')
        base_url = 'https://api.fullcontact.com/v3/person.enrich'
        while entities:
            entity = entities.pop(0)
            payload = {'email': entity}
            headers = {'Authorization': 'Bearer ' + api_key}
            resp = self.request('POST', base_url, json=payload, headers=headers)
            if resp.status_code == 200:

                # parse contact information
                name = resp.json().get('fullName')
                if name:
                    first_name, middle_name, last_name = parse_name(name)
                    self.alert(name)
                emails = [entity]
                new_emails = resp.json()['details'].get('emails') or []
                for email in new_emails:
                    emails.append(email['value'])
                    self.alert(email['value'])
                title = resp.json().get('title')
                organization = resp.json().get('organization')
                if title and organization:
                    title = f"{title} at {organization}"
                elif organization:
                    title = f"Employee at {organization}"
                if title:
                    self.alert(title)

                # parse location
                region = resp.json().get('location')
                if region:
                    self.alert(region)

                # insert contacts
                for email in emails:
                    self.insert_contacts(first_name=first_name, middle_name=middle_name, last_name=last_name, title=title,
                                         email=email, region=region)

                # parse and insert profiles
                for resource in ['twitter', 'linkedin', 'facebook']:
                    url = resp.json().get(resource)
                    if url:
                        username = url.split('/')[-1]
                        self.alert(url)
                        self.insert_profiles(username=username, url=url, resource=resource, category='social')

            elif resp.status_code == 202:
                # add emails queued by fullcontact back to the list
                entities.append(entity)
                self.output(f"{entity} queued and added back to the list.")
            else:
                self.output(f"{entity} - {resp.json()['message']}")
            # 600 requests per minute api rate limit
            sleep(.1)
