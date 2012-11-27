
import unittest

from monteur.distribution.release import Release
from monteur.distribution.workingset import ReleaseSet


class ReleaseTestCase(unittest.TestCase):
    """Test a release
    """

    def test_release_set(self):
        """Test a release set, container for release
        """
        packages = ReleaseSet()
        self.assertEqual(len(packages), 0)
        self.assertFalse('zeam.software' in packages)
        packages.add(Release(name='zeam.software'))
        self.assertEqual(len(packages), 1)
        packages.add(Release(name='zeam.software'))
        self.assertEqual(len(packages), 1)
