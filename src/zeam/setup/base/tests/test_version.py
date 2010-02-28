
import unittest

from zeam.setup.base.distribution import Version

class VersionTestCase(unittest.TestCase):

    def test_parse(self):
        version = Version.parse('1.2a1')
        self.assertEqual(str(version), '1.2a1')


