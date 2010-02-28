
import unittest

from zeam.setup.base.version import Version, Requirement, Requirements


class VersionTestCase(unittest.TestCase):
    """Test version implementation.
    """

    def test_parse(self):
        """Test version parsing
        """
        for version in ['1.2a1', '0.12', '1dev']:
            parsed_version = Version.parse(version)
            self.assertEqual(str(parsed_version), version)

    def test_comparaison(self):
        """Test comparaison between versions
        """
        v1 = Version.parse('2a1')
        v2 = Version.parse('2b1')
        self.failUnless(v1 < v2)
        self.failUnless(v2 > v1)

    def test_sort(self):
        """Test version sorting
        """
        versions = ['1.4', '0.1', '1.4a1', '2.0', '1.4b1']
        parsed_versions = map(Version.parse, versions)
        parsed_versions.sort()
        self.assertEqual(
            map(str, parsed_versions),
            ['0.1', '1.4a1', '1.4b1', '1.4', '2'])


class RequirementTestCase(unittest.TestCase):
    """Test requirement implementation.
    """

    def test_parse(self):
        """Test requirement parsing and printing
        """
        req = Requirement.parse('test.software')
        self.assertEquals(req.name, 'test.software')
        self.assertEquals(req.versions, [])
        self.assertEquals(str(req), 'test.software')

        req = Requirement.parse('MySoft ==2.3, <=2.4')
        self.assertEquals(req.name, 'MySoft')
        self.assertEquals(len(req.versions), 2)
        self.assertEquals(str(req), 'MySoft==2.3,<=2.4')

        req = Requirement.parse('Zope2>=2.12.3dev')
        self.assertEquals(req.name, 'Zope2')
        self.assertEquals(len(req.versions), 1)
        self.assertEquals(str(req.versions[0][1]), '2.12.3dev')
        self.assertEquals(str(req), 'Zope2>=2.12.3dev')


class RequirementsTestCase(unittest.TestCase):
    """Test requirements implementation.
    """

    def test_parse(self):
        """Test requirements parsing and printing
        """
        reqs = Requirements.parse([])
        self.assertEquals(len(reqs), 0)
        self.assertEquals(len(reqs.requirements), 0)

        reqs = Requirements.parse('test.software')
        self.assertEquals(len(reqs), 1)
        self.assertEquals(len(reqs.requirements), 1)
        self.assertEquals(str(reqs), 'test.software')

        reqs = Requirements.parse(
            ['zeam.form.base',
             'zeam.test>=2.1',
             'zope.testing<=3.7dev'])
        self.assertEquals(len(reqs), 3)
        self.assertEquals(len(reqs.requirements), 3)
        self.assertEquals(
            str(reqs),
            'zeam.form.base\nzeam.test>=2.1\nzope.testing<=3.7dev')
