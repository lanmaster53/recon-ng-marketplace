from recon.core.module import BaseModule
import csv
import gzip
import os
import warnings
from io import BytesIO


class Module(BaseModule):

    meta = {
        'name': 'Interesting File Finder',
        'author': 'Tim Tomes (@lanmaster53), thrapt (thrapt@gmail.com), Jay Turla (@shipcod3), and Mark Jeffery',
        'version': '1.2',
        'description': 'Checks hosts for interesting files in predictable locations.',
        'comments': (
            'Files: robots.txt, sitemap.xml, sitemap.xml.gz, crossdomain.xml, phpinfo.php, test.php, elmah.axd, server-status, jmx-console/, admin-console/, web-console/',
            f'CSV Default: {os.path.join(BaseModule.data_path, "interesting_files_verify.csv")}',
            'Google Dorks:',
            '\tinurl:robots.txt ext:txt',
            '\tinurl:elmah.axd ext:axd intitle:"Error log for"',
            '\tinurl:server-status "Apache Status"',
        ),
        'query': 'SELECT DISTINCT host FROM hosts WHERE host IS NOT NULL',
        'options': (
            ('csv_file', os.path.join(BaseModule.data_path, 'interesting_files_verify.csv'),
             True, 'custom filename map'),
            ('download', True, True, 'download discovered files'),
            ('protocol', 'http', True, 'request protocol'),
            ('port', 80, True, 'request port'),
        ),
        'files': ['interesting_files_verify.csv'],
    }

    def read_filenames_csv(self):
        with open(os.path.expanduser(self.options['csv_file'])) as csvfile:
            fname_csv = csv.reader(csvfile, delimiter=',', quotechar='"')
            # verification string used to prevent false positives;
            #   eg: if robots.txt redirects to login page & returns a 200
            return [(fname, verify_str) for (fname, verify_str) in fname_csv]

    def uncompress(self, data_gz):
        inbuffer = BytesIO(data_gz.encode())
        data_ct = ''
        f = gzip.GzipFile(mode='rb', fileobj=inbuffer)
        try:
            data_ct = f.read()
        except IOError:
            pass
        f.close()
        return data_ct

    def module_run(self, hosts):
        download = self.options['download']
        protocol = self.options['protocol']
        port = self.options['port']
        # ignore unicode warnings when trying to un-gzip text type 200 repsonses
        warnings.simplefilter("ignore")
        filetypes = self.read_filenames_csv()
        count = 0

        for host in hosts:
            for (filename, verify) in filetypes:
                url = f"{protocol}://{host}:{port}/{filename}"
                try:
                    resp = self.request('GET', url)
                    code = resp.status_code
                except KeyboardInterrupt:
                    raise KeyboardInterrupt
                except:
                    code = 'Error'
                if code == 200:
                    # uncompress if necessary
                    text = ('.gz' in filename and self.uncompress(resp.text)) or resp.text
                    # check for file type since many custom 404s are returned as 200s
                    if verify.lower() in text.lower():
                        self.alert(f"{url} => {code}. '{filename}' found!")
                        # urls that end with '/' are not necessary to download
                        if download and not filename.endswith("/"):
                            filepath = f"{self.workspace}/{protocol}_{host}_{filename}"
                            dl = open(filepath, 'w')
                            dl.write(resp.text)
                            dl.close()
                        count += 1
                    else:
                        self.output(f"{url} => {code}. '{filename}' found but unverified.")
                else:
                    self.verbose(f"{url} => {code}")
        self.output(f"{count} interesting files found.")
        if download and count:
            self.output(f"Files downloaded to '{self.workspace}/'")
