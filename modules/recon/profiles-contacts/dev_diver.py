from recon.core.module import BaseModule
from recon.utils.parsers import parse_name
from urllib.parse import unquote_plus
import json
import re
import time

class Module(BaseModule):

    meta = {
        'name': 'Dev Diver Repository Activity Examiner',
        'author': 'Micah Hoffman (@WebBreacher)',
        'version': '1.1',
        'description': 'Searches public code repositories for information about a given username.',
        'query': 'SELECT DISTINCT username FROM profiles WHERE username IS NOT NULL',
    }

    # Add a method for each repository
    def github(self, username):
        self.verbose('Checking Github...')
        url = f"https://api.github.com/users/{username}"
        resp = self.request('GET', url)
        data = resp.json()
        if 'login' in data:
            self.alert(f"Github username found - ({url})")
            # extract data from the optional fields
            gitName    = data['name'] if 'name' in data else None
            gitCompany = data['company'] if 'company' in data else None
            gitBlog    = data['blog'] if 'blog' in data else None
            gitLoc     = data['location'] if 'location' in data else None
            gitEmail   = data['email'] if 'email' in data else None
            gitBio     = data['bio'] if 'bio' in data else None
            gitJoin    = data['created_at'].split('T')
            gitUpdate  = data['updated_at'].split('T')
            # build and display a table of the results
            tdata = []
            tdata.append(['Resource', 'Github'])
            tdata.append(['User Name', data['login']])
            tdata.append(['Real Name', gitName]) if gitName else None
            tdata.append(['Profile URL', data['html_url']])
            tdata.append(['Avatar URL', data['avatar_url']])
            tdata.append(['Location', gitLoc])
            tdata.append(['Company', gitCompany])
            tdata.append(['Blog URL', gitBlog])
            tdata.append(['Email', gitEmail])
            tdata.append(['Bio', gitBio])
            tdata.append(['Followers', data['followers']])
            tdata.append(['ID', data['id']])
            tdata.append(['Joined', gitJoin[0]])
            tdata.append(['Updated', gitUpdate[0]])
            self.table(tdata, title='Github')
            # add the pertinent information to the database
            if not gitName: gitName = username
            fname, mname, lname = parse_name(gitName)
            self.insert_contacts(first_name=fname, middle_name=mname, last_name=lname, title='Github Contributor')
        else:
            self.output('Github username not found.')

    def bitbucket(self, username):
        self.verbose('Checking Bitbucket...')
        url = f"https://bitbucket.org/api/2.0/users/{username}"
        resp = self.request('GET', url)
        data = resp.json()
        if 'username' in data:
            self.alert(f"Bitbucket username found - ({url})")
            # extract data from the optional fields
            bbName = data['display_name']
            bbJoin = data['created_on'].split('T')
            # build and display a table of the results
            tdata = []
            tdata.append(['Resource', 'Bitbucket'])
            tdata.append(['User Name', data['username']])
            tdata.append(['Display Name', bbName])
            tdata.append(['Location', data['location']])
            tdata.append(['Joined', bbJoin[0]])
            tdata.append(['Personal URL', data['website']])
            tdata.append(['Bitbucket URL', data['links']['html']['href']])
            #tdata.append(['Avatar URL', data['user']['avatar']]) # This works but is SOOOO long it messes up the table
            self.table(tdata, title='Bitbucket')
            # add the pertinent information to the database
            if not bbName: bbName = username
            fname, mname, lname = parse_name(bbName)
            self.insert_contacts(first_name=fname, middle_name=mname, last_name=lname, title='Bitbucket Contributor')
        else:
            self.output('Bitbucket username not found.')

    def sourceforge(self, username):
        self.verbose('Checking SourceForge...')
        url = f"http://sourceforge.net/u/{username}/profile/"
        resp = self.request('GET', url)
        sfName = re.search(r'<title>(.+) / Profile', resp.text)
        if sfName:
            self.alert(f"Sourceforge username found - ({url})")
            # extract data
            sfJoin = re.search(r'<dt>Joined:</dt><dd>\s*(\d\d\d\d-\d\d-\d\d) ', resp.text)
            sfLocation = re.search(r'<dt>Location:</dt><dd>\s*(\w.*)', resp.text)
            sfGender = re.search(r'<dt>Gender:</dt><dd>\s*(\w.*)', resp.text)
            sfProjects = re.findall(r'class="project-info">\s*<a href="/p/.+/">(.+)</a>', resp.text)
            # establish non-match values
            sfName = sfName.group(1)
            sfJoin = sfJoin.group(1) if sfJoin else None
            sfLocation = sfLocation.group(1) if sfLocation else None
            sfGender = sfGender.group(1) if sfGender else None
            # build and display a table of the results
            tdata = []
            tdata.append(['Resource', 'Sourceforge'])
            tdata.append(['Name', sfName])
            tdata.append(['Profile URL', url])
            tdata.append(['Joined', sfJoin])
            tdata.append(['Location', sfLocation])
            tdata.append(['Gender', sfGender])
            for sfProj in sfProjects:
                tdata.append(['Projects', sfProj])
            self.table(tdata, title='Sourceforge')
            # add the pertinent information to the database
            if not sfName: sfName = username
            fname, mname, lname = parse_name(sfName)
            self.insert_contacts(first_name=fname, middle_name=mname, last_name=lname, title='Sourceforge Contributor')
        else:
            self.output('Sourceforge username not found.')

    def codeplex(self, username):
        self.verbose('Checking CodePlex...')
        url = f"http://www.codeplex.com/site/users/view/{username}"
        resp = self.request('GET', url)
        cpName = re.search(r'<h1 class="user_name" style="display: inline">(.+)</h1>', resp.text)
        if cpName:
            self.alert(f"CodePlex username found - ({url})")
            # extract data
            cpJoin = re.search(r'Member Since<span class="user_float">([A-Z].+[0-9])</span>', resp.text)
            cpLast = re.search(r'Last Visit<span class="user_float">([A-Z].+[0-9])</span>', resp.text)
            cpCoordinator = re.search(r'(?s)<p class="OverflowHidden">(.*?)</p>', resp.text)
            # establish non-match values
            cpName = cpName.group(1) if cpName else None
            cpJoin = cpJoin.group(1) if cpJoin else 'January 1, 1900'
            cpLast = cpLast.group(1) if cpLast else 'January 1, 1900'
            cpCoordinator = cpCoordinator.group(1) if cpCoordinator else ''
            # build and display a table of the results
            tdata = []
            tdata.append(['Resource', 'CodePlex'])
            tdata.append(['Name', cpName])
            tdata.append(['Profile URL', url])
            tdata.append(['Joined', time.strftime('%Y-%m-%d', time.strptime(cpJoin, '%B %d, %Y'))])
            tdata.append(['Date Last', time.strftime('%Y-%m-%d', time.strptime(cpLast, '%B %d, %Y'))])
            cpCoordProject = re.findall(r'<a href="(http://.+)/" title=".+">(.+)<br /></a>', cpCoordinator)
            for cpReposUrl, cpRepos in cpCoordProject:
                tdata.append(['Project', f"{cpRepos} ({cpReposUrl})"])
            self.table(tdata, title='CodePlex')
            # add the pertinent information to the database
            if not cpName: cpName = username
            fname, mname, lname = parse_name(cpName)
            self.insert_contacts(first_name=fname, middle_name=mname, last_name=lname, title='CodePlex Contributor')
        else:
            self.output('CodePlex username not found.')

    def module_run(self, usernames):
        for username in usernames:
            # Check each repository
            self.github(username)
            self.bitbucket(username)
            self.sourceforge(username)
            self.codeplex(username)
