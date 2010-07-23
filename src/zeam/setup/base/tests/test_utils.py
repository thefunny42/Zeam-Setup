
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
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/test/news'),
             ('Other', 'http://test.com/other')])
        self.assertEquals(
            list(rewrite_links('http://test.com/test', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/news'),
             ('Other', 'http://test.com/other')])
        self.assertEquals(
            list(rewrite_links('http://test.com/', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/news'),
             ('Other', 'http://test.com/other')])
        self.assertEquals(
            list(rewrite_links('http://test.com', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/news'),
             ('Other', 'http://test.com/other')])
