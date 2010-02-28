
import unittest

from zeam.setup.base.distribution import Version, Requirement


class VersionTestCase(unittest.TestCase):
    """Test version implementation.
    """

    def test_parse(self):
        """Test version parsing.
        """
        for version in ['1.2a1', '0.12', '1dev']:
            parsed_version = Version.parse(version)
            self.assertEqual(str(parsed_version), version)

    def test_cmp_inf(self):
        """Test comparaison between versions.
        """
        v1 = Version.parse('2a1')
        v2 = Version.parse('2b1')
        self.failUnless(v1 < v2)


class RequirementTestCase(unittest.TestCase):
    """Test requirement implementation.
    """

    def test_parse(self):
        """Test requirement parsing.
        """
        req = Requirement.parse('test.software')
        self.assertEqual(req.name, 'test.software')
        self.assertEqual(req.versions, [])

        req = Requirement.parse('MySoft==2.3,<=2.4')
        self.assertEqual(req.name, 'MySoft')
        self.assertEqual(len(req.versions), 2)

