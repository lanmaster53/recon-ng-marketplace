from recon.core.module import BaseModule
import csv
import os

class Module(BaseModule):

    meta = {
        'name': 'CSV File Creator',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Creates a CSV file containing the specified harvested data.',
        'options': (
            ('table', 'hosts', True, 'source table of data to export'),
            ('filename', os.path.join(BaseModule.workspace, 'results.csv'), True, 'path and filename for output'),
            ('headers', False, True, 'include column headers'),
        ),
    }

    def module_run(self):
        badcharacters = ['@', '-', '=', '+']
        filename = self.options['filename']
        # codecs module not used because the csv module converts to ASCII
        with open(filename, 'w') as outfile:
            table = self.options['table']
            csvwriter = csv.writer(outfile, quoting=csv.QUOTE_ALL)
            if self.options['headers']:
                columns = [c[0] for c in self.get_columns(table)]
                csvwriter.writerow(columns)
            cnt = 0
            rows = self.query(f'SELECT * FROM "{table}" ORDER BY 1')
            for row in rows:
                row = [x if x else '' for x in row]
                if any(row):
                    cnt += 1
                    # prevent csv injection
                    sanitized_row = []
                    for cell in row:
                        if cell and cell[0] in badcharacters:
                            cell = ' '+cell
                        sanitized_row.append(cell)
                    csvwriter.writerow(sanitized_row)
        self.output(f"{cnt} records added to '{filename}'.")
