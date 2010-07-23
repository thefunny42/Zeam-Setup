
import unittest
import operator

from zeam.setup.base.distribution.release import Release
from zeam.setup.base.version import Version, Requirement, Requirements
from zeam.setup.base.version import InvalidRequirement


class VersionTestCase(unittest.TestCase):
    """Test version implementation.
    """

    def test_parse(self):
        """Test version parsing
        """
        for version in ['1.2a1', '0.12', '1dev', '10', '1.10b2']:
            parsed_version = Version.parse(version)
            self.assertEqual(str(parsed_version), version)
        self.assertEqual(str(Version.parse('3.5.0-1')), '3.5final-1')
        self.assertEqual(str(Version.parse('1.dev')), '1dev')

    def test_comparaison_lt_or_gt(self):
        """Test strict comparaison between versions
        """
        v1 = Version.parse('2a1')
        v2 = Version.parse('2b1')
        self.failUnless(v1 < v2)
        self.failIf(v1 > v2)
        self.failUnless(v2 > v1)
        self.failIf(v2 < v1)

    def test_comparaison_le_or_ge(self):
        """Test comparaison beween versions
        """
        v1 = Version.parse('2a1')
        v2 = Version.parse('2b1')
        self.failUnless(v1 <= v2)
        self.failIf(v1 >= v2)
        self.failUnless(v2 >= v1)
        self.failIf(v2 <= v1)

    def test_comparaison_equality(self):
        """Test equality comparaison between versions
        """
        v1 = Version.parse('1.2')
        v2 = Version.parse('1.2')
        v3 = Version.parse('3.3')
        self.failUnless(v1 == v2)
        self.failIf(v1 != v2)
        self.failUnless(v1 != v3)
        self.failIf(v1 == v3)

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
    """Test requirement implementation
    """

    def test_parse(self):
        """Test requirement parsing and printing
        """
        req = Requirement.parse('test.software')
        self.assertEquals(req.name, 'test.software')
        self.assertEquals(req.versions, [])
        self.assertEquals(req.extras, [])
        self.assertEquals(str(req), 'test.software')

        req = Requirement.parse('MySoft ==2.3, <=2.4')
        self.assertEquals(req.name, 'MySoft')
        self.assertEquals(req.extras, [])
        self.assertEquals(len(req.versions), 2)
        self.assertEquals(str(req), 'MySoft==2.3,<=2.4')

        req = Requirement.parse('Zope2>=2.12.3dev')
        self.assertEquals(req.name, 'Zope2')
        self.assertEquals(len(req.versions), 1)
        self.assertEquals(str(req.versions[0][1]), '2.12.3dev')
        self.assertEquals(str(req), 'Zope2>=2.12.3dev')

    def test_parse_extras(self):
        """Test requirement parsing and printing with extras
        """
        req = Requirement.parse('CoolSoft[zca]')
        self.assertEquals(req.name, 'CoolSoft')
        self.assertEquals(req.extras, ['zca'])
        self.assertEquals(req.versions, [])
        self.assertEquals(str(req), 'CoolSoft[zca]')

        req = Requirement.parse('NewSoft [testing,zope.testing , web]')
        self.assertEquals(req.name, 'NewSoft')
        self.assertEquals(req.extras, ['testing', 'zope.testing', 'web'])
        self.assertEquals(req.versions, [])
        self.assertEquals(str(req), 'NewSoft[testing,zope.testing,web]')

        req = Requirement.parse('NewSoft [zope.testing , web] <=2.4, >=1.0')
        self.assertEquals(req.name, 'NewSoft')
        self.assertEquals(req.extras, ['zope.testing', 'web'])
        self.assertEquals(len(req.versions), 2)
        self.assertEquals(str(req), 'NewSoft[zope.testing,web]<=2.4,>=1')

    def test_match(self):
        """Test matching a requirement to a release
        """
        req = Requirement.parse('MySoft >=2.0, <=2.4')
        release = Release('YourSoft', '2.1')
        self.failIf(req.match(release))

        release = Release('MySoft', '2.1')
        self.failUnless(req.match(release))

        release = Release('MySoft', '1.0')
        self.failIf(req.match(release))

    def test_hash(self):
        """Test that requirements are hashable
        """
        req_origin = Requirement.parse("zeam >= 42.0")
        req_lookup = Requirement.parse("zeam >= 42.0")
        req_other = Requirement.parse("zeam >= 12.0")
        self.assertEqual(req_origin, req_lookup)
        self.assertEqual(hash(req_origin), hash(req_lookup))
        self.assertNotEqual(req_origin, req_other)
        self.assertNotEqual(hash(req_origin), hash(req_other))

        data = {}
        data[req_origin] = 10
        self.assertEqual(data.get(req_lookup, None), 10)
        self.assertEqual(data.get(req_other, None), None)

    def test_add(self):
        """Test adding two requirements together
        """
        req_one = Requirement.parse("zeam")
        req_two = Requirement.parse("zeam <= 2.1")
        req_other = Requirement.parse("something.else == 51.0")

        self.assertRaises(InvalidRequirement, operator.add, req_one, 1)
        self.assertRaises(InvalidRequirement, operator.add, req_one, req_other)

        req_result = req_one + req_two
        self.assertEqual(str(req_result), "zeam<=2.1")


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
