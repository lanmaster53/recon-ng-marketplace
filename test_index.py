import unittest
from unittest.mock import patch

from index import merge_lists_of_modules


class MergeListsOfModulesTest(unittest.TestCase):

    @patch('index.datetime')
    def test_adds_new_modules_to_the_index(self, mock_datetime):
        mock_datetime.strftime.return_value = '2026-07-30'
        old_module = {
            'last_updated': '2020-01-01',
            'path': 'recon/existing',
            'version': '1.0',
        }
        new_module = {
            'path': 'recon/new',
            'version': '1.0',
        }

        modules = merge_lists_of_modules(
            [old_module],
            [
                {'path': 'recon/existing', 'version': '1.0'},
                new_module,
            ],
        )

        self.assertEqual(
            modules,
            [
                old_module,
                {
                    **new_module,
                    'last_updated': '2026-07-30',
                },
            ],
        )
        self.assertNotIn('last_updated', new_module)


if __name__ == '__main__':
    unittest.main()
