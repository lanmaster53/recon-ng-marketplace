from recon.core.module import BaseModule
import codecs
import datetime
import os

class Module(BaseModule):

    meta = {
        'name': 'HTML Report Generator',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Creates an HTML report.',
        'options': (
            ('sanitize', True, True, 'mask sensitive data in the report'),
            ('customer', None, True, 'use customer name in the report header'),
            ('creator', None, True, 'use creator name in the report footer'),
            ('filename', os.path.join(BaseModule.workspace, 'results.html'), True, 'path and filename for report output'),
        ),
        'files': ['template_html.html'],
    }

    def build_table(self, table):
        table_content = ''
        table_show = (f"<a id=\"show-{table}\" href=\"javascript:showhide('{table}');\"><p>[+] {table.replace('_', ' ').title()}</p></a>")
        table_hide = (f"<a id=\"hide-{table}\" href=\"javascript:showhide('{table}');\"><p>[-] {table.replace('_', ' ').title()}</p><hr></a>")
        columns = [x[1] for x in self.query(f"PRAGMA table_info('{table}')")]
        columns_str = '", "'.join(columns)
        row_headers = f"<tr><th>{'</th><th>'.join(columns)}</th></tr>"
        rows = self.query(f'SELECT "{columns_str}" FROM "{table}" ORDER BY 1')
        if not rows: return ''
        row_content = ''
        for row in rows:
            values = [self.to_unicode_str(x) if x != None else '' for x in row]
            if table == 'credentials' and values[1] and self.options['sanitize']:
                values[1] = '<omitted>'
            row_content += f"<tr><td>{'</td><td>'.join([self.html_escape(x) for x in values])}</td></tr>\n"
        table_content += f'<div class="container">\n{table_show}\n{table_hide}\n<table name="table" id="{table}">\n{row_headers}\n{row_content}</table>\n</div><br />\n'
        return table_content

    def module_run(self):
        filename = self.options['filename']
        with codecs.open(filename, 'wb', encoding='utf-8') as outfile:
            table_content = ''
            # html template
            template = open(os.path.join(self.data_path, 'template_html.html')).read()
            # custom summary results table
            table_show = '<a id="show-summary" href="javascript:showhide(\'summary\');"><p>[+] Summary</p></a>'
            table_hide = '<a id="hide-summary" href="javascript:showhide(\'summary\');"><p>[-] Summary</p><hr></a>'
            tables = self.get_tables()
            row_headers = '<tr><th>table</th><th>count</th></tr>'
            row_content = ''
            for table in tables:
                query = f'SELECT COUNT(*) FROM "{table}"'
                if table == 'leaks':
                    query = 'SELECT COUNT(DISTINCT leak) FROM credentials WHERE leak IS NOT NULL'
                count = self.query(query)[0][0]
                row_content += f'<tr><td>{table}</td><td class="centered">{count}</td></tr>\n'
            table_content += f'<div class="container">\n{table_show}\n{table_hide}\n<table id="summary">\n{row_headers}\n{row_content}</table>\n</div><br />\n'
            # main content tables
            tables = ['domains', 'companies', 'netblocks', 'locations', 'hosts', 'contacts', 'credentials']
            for table in tables:
                table_content += self.build_table(table)
            # table of leaks associated with credentials
            leaks = self.query('SELECT DISTINCT leak FROM credentials WHERE leak IS NOT NULL')
            if leaks:
                if self.query('SELECT COUNT(*) FROM leaks')[0][0]:
                    columns = [x[1] for x in self.query('PRAGMA table_info(leaks)')]
                    table_content += '<div class="container">\n'
                    table_content += '<a id="show-leaks" href="javascript:showhide(\'leaks\');"><p>[+] Associated Leaks</p></a>\n'
                    table_content += '<a id="hide-leaks" href="javascript:showhide(\'leaks\');"><p>[-] Associated Leaks</p></a>\n'
                    table_content += '<div name="table" id="leaks">\n'
                    for leak in [x[0] for x in leaks]:
                        row_content = ''
                        row = self.query('SELECT * FROM leaks WHERE leak_id=?', (leak,))[0]
                        values = [self.html_escape(x) if x != None else '' for x in row]
                        for i in range(0, len(columns)):
                            row_content += f"<tr><td><strong>{columns[i]}</strong></td><td>{values[i]}</td></tr>\n"
                        table_content += f'<hr>\n<table class="leak">\n{row_content}</table>\n'
                    table_content += '</div>\n</div><br />'
                else:
                    self.output('Associated leak data omitted. Please run the \'leaks_dump\' module to populate the database and try again.')
            # all other tables
            # build exclusions list by extending the list from above
            tables.extend(['leaks', 'pushpins', 'dashboard'])
            tables = [x for x in self.get_tables() if x not in tables]
            for table in tables:
                table_content += self.build_table(table)
            title = self.options['customer']
            creator = self.options['creator']
            created = datetime.datetime.now().strftime('%a, %b %d %Y %H:%M:%S')
            markup = template % (title, table_content, creator, created)
            outfile.write(markup)
        self.output(f"Report generated at '{filename}'.")
