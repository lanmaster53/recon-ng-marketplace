from recon.core.module import BaseModule

class Module(BaseModule):

    meta = {
        'name': 'PwnedList - Leak Details Fetcher',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Queries the local database for information associated with a leak ID. The \'leaks_dump\' module must be used to populate the local database before this module will execute successfully.',
        'query': 'SELECT DISTINCT leak FROM credentials WHERE leak IS NOT NULL',
    }

    def module_run(self, leak_ids):
        self.output(self.ruler*50)
        columns = [x[1] for x in self.query('PRAGMA table_info(leaks)')]
        columns_str = '", "'.join(columns)
        query_str = f'SELECT "{columns_str}" FROM leaks WHERE leak_id=?'
        for leak_id in leak_ids:
            values = self.query(query_str, (leak_id,))
            if not values:
                self.error('Invalid leak ID.')
                continue
            for i in range(0,len(columns)):
                title = ' '.join(columns[i].split('_')).title()
                self.output(f"{title}: {values[0][i]}")
            self.output(self.ruler*50)
