from recon.core.module import BaseModule
from recon.mixins.search import GoogleWebMixin
from PyPDF3 import PdfFileReader
from PyPDF3.utils import PdfReadError
from io import BytesIO
import itertools
import lxml.etree
import olefile
import os
import zipfile

# to do:
# extract email addresses from text
# add info to database

def ole_parser(s):
    ole = olefile.OleFileIO(s)
    meta = ole.get_metadata()
    attrs = meta.DOCSUM_ATTRIBS + meta.SUMMARY_ATTRIBS
    #meta.dump()
    result = {}
    for attr in attrs:
        if hasattr(meta, attr):
            result[attr] = getattr(meta, attr)
    ole.close()
    return result

def ooxml_parser(s):
    zf = zipfile.ZipFile(BytesIO(s))
    doc = lxml.etree.fromstring(zf.read('docProps/core.xml'))
    meta = [(x.tag, x.text) for x in doc.xpath('/*/*', namespaces=doc.nsmap)]
    #print(lxml.etree.tostring(doc, pretty_print=True))
    result = {}
    for el in meta:
        result[el[0].split('}')[-1]] = el[1]
    return result

def pdf_parser(s):
    s = s.strip()
    # required to suppress warning messages
    with open(os.devnull, 'w') as fp:
        pdf = PdfFileReader(BytesIO(s), strict=False, warndest=fp)
    if pdf.isEncrypted:
        try:
            pdf.decrypt('')
        except NotImplementedError:
            return {}
    meta = pdf.getDocumentInfo() or {}
    #print(str(meta))
    result = {}
    for key in meta.keys():
        result[key[1:]] = meta.get(key)
    return result

parsers = {
    'ole': ole_parser,
    'ooxml': ooxml_parser,
    'pdf': pdf_parser,
}

class Module(BaseModule, GoogleWebMixin):

    meta = {
        'name': 'Meta Data Extractor',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.1',
        'description': 'Searches for files associated with the provided domain(s) and extracts any contact related metadata.',
        'comments': (
            'Currently supports doc, docx, xls, xlsx, ppt, pptx, and pdf file types.',
        ),
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': (
            ('extract', False, True, 'extract metadata from discovered files'),
        ),
        'dependencies': ['olefile', 'pypdf3', 'lxml'],
    }

    def module_run(self, domains):
        exts = {
            'ole': ['doc', 'xls', 'ppt'],
            'ooxml': ['docx', 'xlsx', 'pptx'],
            'pdf': ['pdf'],
        }
        search = 'site:%s ' + ' OR '.join([f"filetype:{ext}" for ext in itertools.chain.from_iterable(exts.values())])
        for domain in domains:
            self.heading(domain, level=0)
            results = self.search_google_web(search % domain)
            for result in results:
                self.output(result)
                # metadata extraction
                if self.options['extract']:
                    # parse the extension of the discovered file
                    ext = result.split('.')[-1]
                    # search for the extension in the extensions dictionary
                    # the extensions dictionary key indicates the file type
                    for key in exts:
                        if ext in exts[key]:
                            # check to see if a parser exists for the file type
                            try:
                                func = parsers[key]
                                resp = self.request('GET', result)
                                # validate that the url resulted in a file 
                                if [x for x in ('application', 'binary') if resp.headers['content-type'].startswith(x)]:
                                    meta = func(resp.content)
                                    if meta:
                                        # display the extracted metadata
                                        for key in meta:
                                            if meta[key]:
                                                self.alert(f"{key.title()}: {meta[key]}")
                                    else:
                                        self.output('No meta data found.')
                                else:
                                    self.error(f"Resource not a valid file: {resp.headers['content-type']}")
                            except Exception:
                                self.print_exception()
                            break
            self.alert(f"{len(results)} files found on '{domain}'.")
