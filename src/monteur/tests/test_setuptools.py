
import unittest

from monteur.setuptools.autotools import relative_path


class UtilsTestCase(unittest.TestCase):

    def test_relative_path(self):
        """Test relative path computation
        """
        self.assertEqual(
            relative_path('src/persistance', 'src/persistance/persistance.c'),
            'persistance.c')
        self.assertEqual(
            relative_path('src/persistance', 'src/time/time.c'),
            '../time/time.c')
        self.assertEqual(
            relative_path('src/persistance', 'src/space.c'),
            '../space.c')
        self.assertEqual(
            relative_path('src/persistance', 'src/persistance/space/time.c'),
            'space/time.c')
