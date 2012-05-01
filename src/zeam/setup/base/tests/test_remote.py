

import unittest


class RemoteLinkParserTestCase(unittest.TestCase):
    """Test remote link parsing.
    """

    def test_rewrite(self):
        """Test link rewriting utility
        """
        self.assertEqual(
            list(rewrite_links('http://test.com/', [])),
            [])

        TEST_LINKS = [('http://example.com', 'Example '),
                      ('news', ' News'),
                      ('/other', 'Other'),
                      ('ftp://test.com/download', 'Download')]

        self.assertEqual(
            list(rewrite_links('http://test.com/test/', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/test/news'),
             ('Other', 'http://test.com/other'),
             ('Download', 'ftp://test.com/download')])
        self.assertEqual(
            list(rewrite_links('http://test.com/test', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/news'),
             ('Other', 'http://test.com/other'),
             ('Download', 'ftp://test.com/download')])
        self.assertEqual(
            list(rewrite_links('http://test.com/', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/news'),
             ('Other', 'http://test.com/other'),
             ('Download', 'ftp://test.com/download')])
        self.assertEqual(
            list(rewrite_links('http://test.com', TEST_LINKS)),
            [('Example', 'http://example.com'),
             ('News', 'http://test.com/news'),
             ('Other', 'http://test.com/other'),
             ('Download', 'ftp://test.com/download')])
