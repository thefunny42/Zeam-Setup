
import unittest

from zeam.setup.base.utils import rewrite_links


class RewriteLinkTestCase(unittest.TestCase):
    """Test rewriting links
    """

    def test_rewrite(self):
        """Test link rewriting utility
        """
        self.assertEquals(
            list(rewrite_links('http://test.com/', [])),
            [])

        TEST_LINKS = [('http://example.com', 'Example '),
                      ('news', ' News'),
                      ('/other', 'Other')]

        self.assertEquals(
            list(rewrite_links('http://test.com/test/', TEST_LINKS)),
            [('example', 'http://example.com'),
             ('news', 'http://test.com/test/news'),
             ('other', 'http://test.com/other')])
        self.assertEquals(
            list(rewrite_links('http://test.com/test', TEST_LINKS)),
            [('example', 'http://example.com'),
             ('news', 'http://test.com/news'),
             ('other', 'http://test.com/other')])
        self.assertEquals(
            list(rewrite_links('http://test.com/', TEST_LINKS)),
            [('example', 'http://example.com'),
             ('news', 'http://test.com/news'),
             ('other', 'http://test.com/other')])
        self.assertEquals(
            list(rewrite_links('http://test.com', TEST_LINKS)),
            [('example', 'http://example.com'),
             ('news', 'http://test.com/news'),
             ('other', 'http://test.com/other')])
