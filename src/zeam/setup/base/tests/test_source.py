
import unittest

from zeam.setup.base.sources import get_release_from_name


class MockSource(object):
    """Fake source to trace which release is created.
    """
    factory = lambda *args: args


class SourceTestCase(unittest.TestCase):
    """Test source acquiring and processing.
    """

    def test_invalid_release_from_name(self):
        """Test release name that doesn't parse
        """
        source = MockSource()

        self.assertEqual(
            get_release_from_name(source, 'setup.tar.gz'), None)
        self.assertEqual(
            get_release_from_name(source, 'setup-0.1dev.html'), None)
        self.assertEqual(
            get_release_from_name(source, 'setup-1.0-py2.7-win32.exe'), None)

    def test_release_from_name(self):
        """Test release name parsing
        """
        source = MockSource()

        self.assertEqual(
            get_release_from_name(source, 'setup-0.1dev.tar.gz'),
            (source, source, 'setup', '0.1dev', 'tar.gz', None, None, None))
        self.assertEqual(
            get_release_from_name(source, 'setup-0.1dev-py2.4.tar.gz'),
            (source, source, 'setup', '0.1dev', 'tar.gz', None, '2.4', None))
        self.assertEqual(
            get_release_from_name(source, 'setup-2.0beta1-py2.6.tar.gz'),
            (source, source, 'setup', '2.0beta1', 'tar.gz', None, '2.6', None))
        self.assertEqual(
            get_release_from_name(source, 'setup-2.0-py2.6-linux.tar.gz'),
            (source, source, 'setup', '2.0', 'tar.gz', None, '2.6', 'linux'))
        self.assertEqual(
            get_release_from_name(source, 'setup-1.0-py2.7-win32.tar.gz'),
            (source, source, 'setup', '1.0', 'tar.gz', None, '2.7', 'win32'))
        self.assertEqual(
            get_release_from_name(source, 'setup-1.0-py2.7.tgz'),
            (source, source, 'setup', '1.0', 'tgz', None, '2.7', None))
        self.assertEqual(
            get_release_from_name(source, 'setup-1.0-py2.7.zip'),
            (source, source, 'setup', '1.0', 'zip', None, '2.7', None))
        self.assertEqual(
            get_release_from_name(source, 'setup-1.0-py2.7-win32.egg'),
            (source, source, 'setup', '1.0', 'egg', None, '2.7', 'win32'))
