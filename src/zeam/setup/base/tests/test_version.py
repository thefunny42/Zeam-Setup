
import unittest
import operator

from zeam.setup.base.distribution.release import Release
from zeam.setup.base.version import Version, Requirement, Requirements
from zeam.setup.base.version import InvalidRequirement, IncompatibleRequirement
from zeam.setup.base.version import InvalidVersion


class VersionTestCase(unittest.TestCase):
    """Test version implementation.
    """

    def test_parse(self):
        """Test version parsing
        """
        for version in ['1.2a1', '0.12', '1.10b2']:
            parsed_version = Version.parse(version)
            self.assertEqual(str(parsed_version), version)
        self.assertEqual(str(Version.parse('3.5.0-1')), '3.5-1')
        self.assertEqual(str(Version.parse('3.5final-1')), '3.5-1')
        self.assertEqual(str(Version.parse('3.5alpha2')), '3.5a2')
        self.assertEqual(str(Version.parse('3.5beta1')), '3.5b1')
        self.assertEqual(str(Version.parse('3.5.post42')), '3.5-42')
        self.assertEqual(str(Version.parse('1b2.2')), '1.0b2.2')
        self.assertEqual(str(Version.parse('1.dev')), '1.0dev')
        self.assertEqual(str(Version.parse('1.0dev')), '1.0dev')
        self.assertEqual(str(Version.parse('1.0.0dev')), '1.0dev')
        self.assertEqual(str(Version.parse('10')), '10.0')

        self.assertRaises(InvalidVersion, Version.parse, 'lol.best-of-world')

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
        versions = ['1.4', '0.1', '1.4a1', '2.0.0', '1.4b1']
        parsed_versions = map(Version.parse, versions)
        parsed_versions.sort()
        self.assertEqual(
            map(str, parsed_versions),
            ['0.1', '1.4a1', '1.4b1', '1.4', '2.0'])


class RequirementTestCase(unittest.TestCase):
    """Test requirement implementation
    """

    def test_parse(self):
        """Test requirement parsing and printing
        """
        req = Requirement.parse('test.software')
        self.assertEquals(req.name, 'test.software')
        self.assertEquals(req.versions, [])
        self.assertEquals(req.extras, set())
        self.assertEquals(str(req), 'test.software')

        req = Requirement.parse('MySoft ==2.3, <=2.4')
        self.assertEquals(req.name, 'MySoft')
        self.assertEquals(req.extras, set())
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
        self.assertEquals(req.extras, set(['zca']))
        self.assertEquals(req.versions, [])
        self.assertEquals(str(req), 'CoolSoft[zca]')

        req = Requirement.parse('NewSoft [testing,zope.testing , web]')
        self.assertEquals(req.name, 'NewSoft')
        self.assertEquals(req.extras, set(['testing', 'zope.testing', 'web']))
        self.assertEquals(req.versions, [])
        self.assertEquals(str(req), 'NewSoft[testing,web,zope.testing]')

        req = Requirement.parse('NewSoft [zope.testing , web] <=2.4, >=1.0')
        self.assertEquals(req.name, 'NewSoft')
        self.assertEquals(req.extras, set(['zope.testing', 'web']))
        self.assertEquals(len(req.versions), 2)
        self.assertEquals(str(req), 'NewSoft[web,zope.testing]<=2.4,>=1.0')

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

    def test_add_reduce(self):
        """Test than when adding two requirements together
        version are simplified.
        """
        TESTS = [
            ['zeam ==1.1', 'zeam ==1.1', 'zeam==1.1'],
            ['zeam ==1.1', 'zeam >=0.9', 'zeam==1.1'],
            ['zeam ==1.1', 'zeam >=1.1', 'zeam==1.1'],
            ['zeam ==1.1', 'zeam <=9.1', 'zeam==1.1'],
            ['zeam ==1.1', 'zeam <=1.1', 'zeam==1.1'],
            ['zeam !=1.1', 'zeam !=1.1', 'zeam!=1.1'],
            ['zeam !=3.1', 'zeam <=1.1', 'zeam<=1.1'],
            ['zeam !=3.1', 'zeam <=3.1', 'zeam<=3.1,!=3.1'],
            ['zeam !=3.1', 'zeam <=4.1', 'zeam!=3.1,<=4.1'],
            ['zeam !=3.1', 'zeam >=4.1', 'zeam>=4.1'],
            ['zeam !=3.1', 'zeam >=1.1', 'zeam>=1.1,!=3.1'],
            ['zeam !=3.1', 'zeam >=3.1', 'zeam>=3.1,!=3.1'],
            ['zeam >=2.4,>=4.2', 'zeam >=3.1', 'zeam>=4.2'],
            ['zeam >=2.4', 'zeam !=0.4', 'zeam>=2.4'],
            ['zeam >=2.4', 'zeam !=4.4', 'zeam>=2.4,!=4.4'],
            ['zeam >=2.4', 'zeam !=2.4', 'zeam!=2.4,>=2.4'],
            ['zeam >=2.4', 'zeam ==4.4', 'zeam==4.4'],
            ['zeam >=4.4', 'zeam ==4.4', 'zeam==4.4'],
            ['zeam >=2.4', 'zeam <=4.4', 'zeam>=2.4,<=4.4'],
            ['zeam >=2.4', 'zeam <=2.4', 'zeam<=2.4,>=2.4'],
            ['zeam <=2.4', 'zeam ==1.4', 'zeam==1.4'],
            ['zeam <=1.4', 'zeam ==1.4', 'zeam==1.4'],
            ['zeam <=2.4', 'zeam !=1.4', 'zeam!=1.4,<=2.4'],
            ['zeam <=2.4', 'zeam !=2.4', 'zeam!=2.4,<=2.4'],
            ['zeam <=2.4', 'zeam !=4.4', 'zeam<=2.4'],
            ['zeam <=2.4', 'zeam >=1.4', 'zeam>=1.4,<=2.4'],
            ['zeam <=2.4', 'zeam >=2.4', 'zeam>=2.4,<=2.4'],
            ]

        for index, test_entry in enumerate(TESTS):
            first, second, expected = test_entry
            req_first = Requirement.parse(first)
            req_second = Requirement.parse(second)

            req_result = req_first + req_second
            result = str(req_result)
            self.assertEqual(
                result, expected,
                msg=u'"%s" + "%s" != "%s" (got %s, test %d)' % (
                    first, second, expected, result, index))

    def test_add_extras(self):
        """Test than extras are keeping and extending while adding
        two requirements together.
        """
        TESTS = [
            ['zeam[nuclear] <=2.1', 'zeam >=1.9',
             'zeam[nuclear]>=1.9,<=2.1'],
            ['zeam <=2.1', 'zeam[nuclear] >=1.9',
             'zeam[nuclear]>=1.9,<=2.1'],
            ['zeam[nuclear] <=2.1', 'zeam[nuclear,web] >=1.9',
             'zeam[nuclear,web]>=1.9,<=2.1'],
            ['zeam[nuclear] <=2.1', 'zeam[web,tests]',
             'zeam[nuclear,tests,web]<=2.1'],
            ]

        for index, test_entry in enumerate(TESTS):
            first, second, expected = test_entry
            req_first = Requirement.parse(first)
            req_second = Requirement.parse(second)

            req_result = req_first + req_second
            result = str(req_result)
            self.assertEqual(
                result, expected,
                msg=u'"%s" + "%s" != "%s" (got %s, test %d)' % (
                    first, second, expected, result, index))

    def test_add_reduce_failed(self):
        """Test than when adding two incompatible requirements
        together an error is raised.
        """
        TESTS = [
            ['zeam ==2.4', 'zeam ==1.1'],
            ['zeam ==2.4', 'zeam !=2.4'],
            ['zeam ==2.4', 'zeam <=1.1'],
            ['zeam ==2.4', 'zeam >=4.1'],
            ['zeam !=2.4', 'zeam ==2.4'],
            ['zeam >=2.4', 'zeam <=1.1'],
            ['zeam >=2.4', 'zeam ==1.1'],
            ['zeam <=2.4', 'zeam >=5.1'],
            ['zeam <=2.4', 'zeam ==5.1'],
            ]

        for first, second in TESTS:
            req_first = Requirement.parse(first)
            req_second = Requirement.parse(second)

            try:
                req_first + req_second
            except IncompatibleRequirement:
                continue
            else:
                self.fail(u'"%s" + "%s" should not work' % (first, second))


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
            str(reqs).split('\n'),
            ['zeam.form.base',
             'zeam.test>=2.1',
             'zope.testing<=3.7dev'])

    def test_add(self):
        """Test adding two sets of requirements together
        """
        reqs = Requirements.parse(
            ['zeam.form.base',
             'zeam.test>=2.1',
             'zope.testing<=3.7dev'])
        self.assertRaises(ValueError, operator.add, reqs, 42)
        self.assertRaises(ValueError, operator.add, reqs, "zeam >= 1.1")

        other_reqs = Requirements.parse(
            ['zeam.form.ztk[test] >=1.0b1',
             'zeam.test <=4.0, !=3.0'])

        result_reqs = reqs + other_reqs

        self.assertEquals(
            str(result_reqs).split('\n'),
            ['zeam.form.base',
             'zeam.form.ztk[test]>=1.0b1',
             'zeam.test>=2.1,!=3.0,<=4.0',
             'zope.testing<=3.7dev'])

    def test_add_fail(self):
        """Test adding two incompatible set of requirements together
        """
        reqs = Requirements.parse(
            ['zeam.form.base',
             'zeam.test>=2.1'])
        other_reqs = Requirements.parse(
            ['zeam.form.ztk[test] >=1.0b1',
             'zeam.test <=1.0'])

        self.assertRaises(
            IncompatibleRequirement, operator.add, reqs, other_reqs)
