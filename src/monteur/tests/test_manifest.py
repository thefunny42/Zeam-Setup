
import os
import unittest

from monteur.distribution.manifest import parse_manifest


def get_test_file(name):
    # Return the path to the test directory
    return os.path.join(os.path.dirname(__file__), 'data', name)


class ManifestTestCase(unittest.TestCase):
    """Test manifest parsing.
    """

    def test_parse_simple(self):
        """Parse a manifest with only simple rules
        """
        data = parse_manifest(get_test_file('manifest_simple.ini'))
        self.assertEqual(
            data,
            ({'src/package/': ['__init__.py'],
              'src/': ['README.txt'],
              './': ['setup.py']},
             {}))

    def test_parse_recursive(self):
        """Parse a manifest with recursive rules
        """
        data = parse_manifest(get_test_file('manifest_recursive.ini'))
        self.assertEqual(
            data,
            ({'./': ['setup.py']},
             {'src/': ['*.txt', '*.ini'],
              './': ['*.py']}))
