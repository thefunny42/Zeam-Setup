
import unittest

from zeam.setup.base.version import Requirement
from zeam.setup.base.distribution.release import Release
from zeam.setup.base.error import InstallationError


class SoftwareTestCase(unittest.TestCase):
    """Test a software, that contains releases.
    """

    def test_software(self):
        """Test adding releases to a software
        """
        soft = Software('MySoft')

        self.assertEqual(len(soft), 0)
        self.assertRaises(
            InstallationError, soft.add, Release('YourSoft', '2.0'))
        self.assertEqual(len(soft), 0)

        soft.add(Release('MySoft', '1.0'))
        soft.add(Release('MySoft', '1.2'))
        soft.add(Release('MySoft', '2.0'))
        soft.add(Release('MySoft', '2.1'))
        self.assertEqual(len(soft), 4)

    def test_matching_requirements(self):
        """Test matching a requirement to a software
        """
        soft = Software('MySoft')
        soft.add(Release('MySoft', '1.0'))
        soft.add(Release('MySoft', '1.2'))
        soft.add(Release('MySoft', '2.0'))
        soft.add(Release('MySoft', '2.1'))

        req = Requirement.parse('MySoft>=2.0')
        match = soft[req]
        self.failUnless(isinstance(match, Software))
        self.assertEqual(soft.name, match.name)
        self.assertEqual(len(match), 2)
        self.assertEqual(
            map(str, match.releases),
            ['<Release for MySoft version 2.0>',
             '<Release for MySoft version 2.1>'])
