
import unittest

from monteur.sources.utils import parse_filename
from monteur.version import Version


class SourceTestCase(unittest.TestCase):
    """Test source acquiring and processing.
    """

    def test_invalid_parse_filename(self):
        """Test installer name that doesn't parse
        """
        self.assertEqual(parse_filename('setup.tar.gz'), {})
        self.assertEqual(parse_filename('setup-0.1dev.html'), {})
        self.assertEqual(parse_filename('setup-1.0-py2.7-win32.exe'), {})

    def test_parse_filename(self):
        """Test installer name parsing
        """
        self.assertEqual(
            parse_filename('ZODB3-3.9.1a10.tar.gz'),
            {'name': 'ZODB3', 'format': 'tar.gz',
             'pyversion': None, 'platform': None,
             'version': Version.parse('3.9.1a10')})
        self.assertEqual(
            parse_filename('setup-0.1dev.tar.gz'),
            {'name': 'setup', 'format': 'tar.gz',
             'pyversion': None, 'platform': None,
             'version': Version.parse('0.1dev')})
        self.assertEqual(
            parse_filename('setup-0.1dev-py2.4.tar.gz'),
            {'name': 'setup', 'format': 'tar.gz',
             'pyversion': '2.4', 'platform': None,
             'version': Version.parse('0.1dev')})
        self.assertEqual(
            parse_filename('setup-2.0beta1-py2.6.tar.gz'),
            {'name': 'setup', 'format': 'tar.gz',
             'pyversion': '2.6', 'platform': None,
             'version': Version.parse('2.0b1')})
        self.assertEqual(
            parse_filename('setup-2.0-py2.6-linux.tar.gz'),
            {'name': 'setup', 'format': 'tar.gz',
             'pyversion': '2.6', 'platform': 'linux',
             'version': Version.parse('2.0')})
        self.assertEqual(
            parse_filename('setup-1.0-py2.7-win32.tar.gz'),
            {'name': 'setup', 'format': 'tar.gz',
             'pyversion': '2.7', 'platform': 'win32',
             'version': Version.parse('1.0')})
        self.assertEqual(
            parse_filename('setup-1.0a1-py2.7.tgz'),
            {'name': 'setup', 'format': 'tgz',
             'pyversion': '2.7', 'platform': None,
             'version': Version.parse('1.0a1')})
        self.assertEqual(
            parse_filename('setup-1.0-py2.7.zip'),
            {'name': 'setup', 'format': 'zip',
             'pyversion': '2.7', 'platform': None,
             'version': Version.parse('1.0')})
        self.assertEqual(
            parse_filename('setup-1.0-py2.7-win32.egg'),
            {'name': 'setup', 'format': 'egg',
             'pyversion': '2.7', 'platform': 'win32',
             'version': Version.parse('1.0')})
        self.assertEqual(
            parse_filename('setup-1.0-py2.7-win-amd64.egg'),
            {'name': 'setup', 'format': 'egg',
             'pyversion': '2.7', 'platform': 'win-amd64',
             'version': Version.parse('1.0')})
        self.assertEqual(
            parse_filename('setup-3.5.0-1.tar.gz'),
            {'name': 'setup', 'format': 'tar.gz',
             'pyversion': None, 'platform': None,
             'version': Version.parse('3.5-1')})
        self.assertEqual(
            parse_filename('setup-3.5.0-1-py2.6-mac.tar.gz'),
            {'name': 'setup', 'format': 'tar.gz',
             'pyversion': '2.6', 'platform': 'mac',
             'version': Version.parse('3.5-1')})
        self.assertEqual(
            parse_filename('setup-3.5.0-1-py2.6-macosx-10.6-x86_64.tar.gz'),
            {'name': 'setup', 'format': 'tar.gz',
             'pyversion': '2.6', 'platform': 'macosx-10.6-x86_64',
             'version': Version.parse('3.5-1')})
        self.assertEqual(
            parse_filename('setuptools-0.6c11-py2.6.egg'),
            {'name': 'setuptools', 'format': 'egg',
             'pyversion': '2.6', 'platform': None,
             'version': Version.parse('0.6c11')})
        self.assertEqual(
            parse_filename('elementtree-1.2.7-20070827.zip'),
            {'name': 'elementtree', 'format': 'zip',
             'pyversion': None, 'platform': None,
             'version': Version.parse('1.2.7-20070827')})
        self.assertEqual(
            parse_filename('elementtree-1.2.7-20070827-preview.zip'),
            {'name': 'elementtree', 'format': 'zip',
             'pyversion': None, 'platform': None,
             'version': Version.parse('1.2.7-20070827-preview')})
        self.assertEqual(
            parse_filename('python-dateutil-1.4.tar.gz'),
            {'name': 'python-dateutil', 'format': 'tar.gz',
             'pyversion': None, 'platform': None,
             'version': Version.parse('1.4')})
        self.assertEqual(
            parse_filename('python-dateutil-1.4dev-r42.tar.gz'),
            {'name': 'python-dateutil', 'format': 'tar.gz',
             'pyversion': None, 'platform': None,
             'version': Version.parse('1.4dev-r42')})
        self.assertEqual(
            parse_filename('python-dateutil-1.4dev-r42-py2.5.tar.gz'),
            {'name': 'python-dateutil', 'format': 'tar.gz',
             'pyversion': '2.5', 'platform': None,
             'version': Version.parse('1.4dev-r42')})
        self.assertEqual(
            parse_filename('python-dateutil-1.4dev-r42-py2.5-win.tar.gz'),
            {'name': 'python-dateutil', 'format': 'tar.gz',
             'pyversion': '2.5', 'platform': 'win',
             'version': Version.parse('1.4dev-r42')})
        self.assertEqual(
            parse_filename('python-dateutil-1.4dev-r42-py2.5-win-i386.tar.gz'),
            {'name': 'python-dateutil', 'format': 'tar.gz',
             'pyversion': '2.5', 'platform': 'win-i386',
             'version': Version.parse('1.4dev-r42')})
        self.assertEqual(
            parse_filename('five.megrok.z3cform-0.1a1-infrae.tar.gz'),
            {'name': 'five.megrok.z3cform', 'format': 'tar.gz',
             'pyversion': None, 'platform': None,
             'version': Version.parse('0.1a1-infrae')})
        self.assertEqual(
            parse_filename('five.megrok.z3cform-0.1a1-infrae-all.tar.gz'),
            {'name': 'five.megrok.z3cform', 'format': 'tar.gz',
             'pyversion': None, 'platform': None,
             'version': Version.parse('0.1a1-infrae-all')})
        self.assertEqual(
            parse_filename(
                'five.megrok.z3cform-0.1a1-infrae-py2.6-linux.tar.gz'),
            {'name': 'five.megrok.z3cform', 'format': 'tar.gz',
             'pyversion': '2.6', 'platform': 'linux',
             'version': Version.parse('0.1a1-infrae')})
        self.assertEqual(
            parse_filename(
                'five.megrok.z3cform-0.1a1-ext-all-py2.6-linux.tar.gz'),
            {'name': 'five.megrok.z3cform', 'format': 'tar.gz',
             'pyversion': '2.6', 'platform': 'linux',
             'version': Version.parse('0.1a1-ext-all')})
        self.assertEqual(
            parse_filename(
                'five.megrok.z3cform-0.1a1-ext-all-py2.6-linux-x86_64.tar.gz'),
            {'name': 'five.megrok.z3cform', 'format': 'tar.gz',
             'pyversion': '2.6', 'platform': 'linux-x86_64',
             'version': Version.parse('0.1a1-ext-all')})

