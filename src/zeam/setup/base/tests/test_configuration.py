
import unittest
import os

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.error import FileError, ConfigurationError


def get_test_file_directory():
    # Return the path to the test directory
    return os.path.join(os.path.dirname(__file__), 'data')


class ConfigurationTestCase(unittest.TestCase):
    """Test the configuration parser
    """

    def test_open(self):
        """Test openning a configuration file
        """
        config = Configuration.read(
            os.path.join(get_test_file_directory(), "test.cfg"))
        self.assertNotEqual(config, None)
        self.failUnless(isinstance(config, Configuration))

        self.assertRaises(FileError, Configuration.read, "not_existing")


class OptionTestCase(unittest.TestCase):
    """Test configuration option
    """

    def setUp(self):
        self.config = Configuration.read(
            os.path.join(get_test_file_directory(), "test.cfg"))
        self.section = self.config['section']

    def test_as_text(self):
        """Test getting an option as text content
        """
        self.assertEqual(
            self.section['option_text'].as_text(),
            u'Description of this nice option')
        self.assertEqual(
            self.section['option_empty'].as_text(),
            u'')

    def test_as_integer(self):
        """Test getting an option as a integer
        """
        self.assertEqual(self.section['option_int'].as_int(), 42)

        self.assertRaises(
            ConfigurationError,
            self.section['option_text'].as_int)
        self.assertRaises(
            ConfigurationError,
            self.section['option_empty'].as_int)

    def test_as_words(self):
        """Test getting an option as a integer
        """
        self.assertEqual(
            self.section['option_words'].as_words(),
            ['Simple', 'word', 'list'])
        self.assertEqual(
            self.section['option_words_lines'].as_words(),
            ['Simple', 'word', 'list'])
        self.assertEqual(
            self.section['option_words_quoted'].as_words(),
            ['Book', 'Language Implementation Patterns'])
        self.assertEqual(
            self.section['option_words_escaped'].as_words(),
            ['Book', 'Language Implementation Patterns'])
        self.assertEqual(
            self.section['option_words_escaped_a1'].as_words(),
            ['Book', '"Language"'])
        self.assertEqual(
            self.section['option_words_escaped_a2'].as_words(),
            ['Book', '\\', 'Book'])

        self.assertRaises(
            ConfigurationError,
            self.section['option_boggus_words'].as_words)

    def test_as_list(self):
        """Test getting an option as a list
        """
        self.assertEqual(
            self.section['option_lines'].as_list(),
            ['In a blue sky', 'A clear light', 'I sucks at this'])
        self.assertEqual(
            self.section['option_text'].as_list(),
            ['Description of this nice option'])
        self.assertEqual(
            self.section['option_empty'].as_list(),
            [])
