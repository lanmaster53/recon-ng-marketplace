from recon.core.module import BaseModule


class Module(BaseModule):

    meta = {
        'name': 'List File Importer',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'version': '1.0',
        'description': 'Imports values from a list file into a database table and column.',
        'options': (
            ('filename', None, True, 'path and filename for list input'),
            ('table', None, True, 'table to import the list values'),
            ('column', None, True, 'column to import the list values'),
        ),
    }
    
    def module_run(self):
        count = 0
        with open(self.options['filename']) as fh:
            lines = fh.read().split()
        method = 'insert_'+self.options['table'].lower()
        if not hasattr(self, method):
            self.error(f'No such table: {options["table"]}')
            return
        func = getattr(self, method)
        for line in lines:
            self.output(line)
            kwargs = {self.options['column']: line}
            count += func(**kwargs)
        self.output(f'{count} new records added.')
