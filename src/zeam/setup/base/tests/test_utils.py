
import unittest

from zeam.setup.base.recipe.commands import Paths
from zeam.setup.base.utils import rewrite_links, relative_uri


class RewriteLinkTestCase(unittest.TestCase):
    """Test rewriting links
    """

    def test_path_container(self):
        """Test path container
        """
        container = Paths()
        container.add('/container/folder/document')
        self.assertEqual(
            container.as_list(),
            ['/container/folder/document'])
        self.assertEqual(
            container.as_list(True),
            ['/container/folder/document'])

        container.add('/document')
        self.assertEqual(
            container.as_list(),
            ['/container/folder/document',
             '/document'])
        self.assertEqual(
            container.as_list(True),
            ['/container/folder/document',
             '/document'])

        container.add('/container/folder/image')
        self.assertEqual(
            container.as_list(),
            ['/container/folder/document',
             '/container/folder/image',
             '/document'])
        self.assertEqual(
            container.as_list(True),
            ['/container/folder/document',
             '/container/folder/image',
             '/document'])

        container.add('/container/folder')
        self.assertEqual(
            container.as_list(),
            ['/container/folder',
             '/container/folder/document',
             '/container/folder/image',
             '/document'])
        self.assertEqual(
            container.as_list(True),
            ['/container/folder',
             '/document'])

    def test_relative_uri(self):
        """Test relative URI.
        """
        self.assertEqual(
            relative_uri('directory/file.txt', 'somefile.txt'),
            'directory/somefile.txt')
        self.assertEqual(
            relative_uri('file.txt', 'somefile.txt'),
            'somefile.txt')
        self.assertEqual(
            relative_uri('directory/file.txt', '/root/somefile.txt'),
            '/root/somefile.txt')
        self.assertEqual(
            relative_uri('directory/file.txt', 'http://localhost/extends.txt'),
            'http://localhost/extends.txt')
        self.assertEqual(
            relative_uri('directory/file.txt', 'https://localhost/extends.txt'),
            'https://localhost/extends.txt')
        self.assertEqual(
            relative_uri('http://localhost/file.txt', 'versions.txt'),
            'http://localhost/versions.txt')
        self.assertEqual(
            relative_uri('https://localhost/file.txt', 'versions.txt'),
            'https://localhost/versions.txt')
        self.assertEqual(
            relative_uri('', 'somefile.txt'),
            'somefile.txt')

    def test_rewrite(self):
        """Test link rewriting utility
        """
        self.assertEqual(
            list(rewrite_links('http://test.com/', [])),
            [])

        TEST_LINKS = [('http://example.com', 'Example '),
                      ('news', ' News'),
                      ('/other', 'Other')]

        self.assertEqual(
            list(rewrite_links('http://test.com/test/', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/test/news'),
             ('Other', 'http://test.com/other')])
        self.assertEqual(
            list(rewrite_links('http://test.com/test', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/news'),
             ('Other', 'http://test.com/other')])
        self.assertEqual(
            list(rewrite_links('http://test.com/', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/news'),
             ('Other', 'http://test.com/other')])
        self.assertEqual(
            list(rewrite_links('http://test.com', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/news'),
             ('Other', 'http://test.com/other')])
