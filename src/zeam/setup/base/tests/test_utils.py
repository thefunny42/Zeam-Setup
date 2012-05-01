
import unittest

from zeam.setup.base.recipe.commands import Paths
from zeam.setup.base.utils import relative_uri


class PathContainerTestCase(unittest.TestCase):
    """Test path containers
    """

    def test_add_and_contains(self):
        """Test adding path into a path container
        """
        container = Paths()
        container.add('/container/folder/document', verify=False)
        self.assertEqual(
            container.as_list(),
            ['/container/folder/document'])
        self.assertEqual(
            container.as_list(True),
            ['/container/folder/document'])

        container.add('/document', verify=False)
        self.assertEqual(
            container.as_list(),
            ['/container/folder/document',
             '/document'])
        self.assertEqual(
            container.as_list(True),
            ['/container/folder/document',
             '/document'])

        container.add('/container/folder/image', verify=False)
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

        container.add('/container/folder', verify=False)
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

        self.assertTrue('/document' in container)
        self.assertTrue('/container/folder/document' in container)
        self.assertFalse('/goinfre' in container)
        self.assertFalse('/container/folder/goinfre' in container)

    def test_extend_contains(self):
        """Test extends path in a path container
        """
        container = Paths()
        self.assertEqual(
            container.as_list(),
            [])
        self.assertEqual(
            container.as_list(True),
            [])

        container.extend(
            ['/document', '/storage/data', '/storage'],
            verify=False)
        self.assertEqual(
            container.as_list(),
            ['/document',
             '/storage',
             '/storage/data'])
        self.assertEqual(
            container.as_list(True),
            ['/document',
             '/storage'])

    def test_update(self):
        """Test update a path in a container with a new one
        """
        container = Paths()
        container.extend(
            ['/document', '/storage/data', '/storage', '/goinfre/files'],
            verify=False)

        self.assertFalse(container.rename('/storage/missing', '/test/failure'))
        self.assertEqual(
            container.as_list(),
            ['/document',
             '/goinfre/files',
             '/storage',
             '/storage/data'])

        self.assertFalse(container.rename('/missing', '/failure'))
        self.assertEqual(
            container.as_list(),
            ['/document',
             '/goinfre/files',
             '/storage',
             '/storage/data'])

        self.assertFalse(container.rename('/goinfre', '/failure'))
        self.assertEqual(
            container.as_list(),
            ['/document',
             '/goinfre/files',
             '/storage',
             '/storage/data'])

        self.assertTrue(container.rename('/document', '/configuration'))
        self.assertEqual(
            container.as_list(),
            ['/configuration',
             '/goinfre/files',
             '/storage',
             '/storage/data'])

        self.assertTrue(container.rename('/goinfre/files', '/goinfre/logs'))
        self.assertEqual(
            container.as_list(),
            ['/configuration',
             '/goinfre/logs',
             '/storage',
             '/storage/data'])

        self.assertTrue(container.rename('/goinfre/logs', '/www/logs'))
        self.assertEqual(
            container.as_list(),
            ['/configuration',
             '/storage',
             '/storage/data',
             '/www/logs'])

        self.assertTrue(container.rename('/www/logs', '/storage/logs'))
        self.assertEqual(
            container.as_list(),
            ['/configuration',
             '/storage',
             '/storage/data',
             '/storage/logs'])



class RewriteLinkTestCase(unittest.TestCase):
    """Test rewriting links
    """

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
