
import os
import re
import logging

from zeam.setup.base.error import ConfigurationError
from zeam.setup.base.utils import open_uri

logger = logging.getLogger('zeam.setup')


SECTION_HEADER = re.compile(r'\[(?P<header>[^]]+)\]')
OPTION_HEADER = re.compile(
    r'(?P<option>[^=\s]+)\s*(?P<operator>=)\s*(?P<value>.*)$')
OPTION_REPLACE = re.compile(
    r'\$\{(?P<section>[^:]*):(?P<option>[^\}]+)\}')


def format_location(filename, start_line, end_line=None):
    """Format location information to report it.
    """
    location = u'%s: line %d' % (filename, start_line)
    if end_line is not None:
        location += u' to %d' % end_line
    return location


class OptionParser(object):
    """Temporary object used to parse an option.
    """

    def __init__(self, name, text, section, filename, line):
        self.name = name
        self.section = section
        self.__filename = filename
        self.__start_line = line
        self.__lines = [(line, text + '\n',)]

    @classmethod
    def new_option(klass, section, text, filename, line):
        is_header = OPTION_HEADER.match(text)
        if is_header:
            return klass(
                is_header.group('option'),
                is_header.group('value'),
                section, filename, line)
        return None

    def add(self, line, text):
        self.__lines.append((line, text + '\n',))

    def done(self, line):
        # XXX Review this
        if line == self.__start_line:
            line = None
        option_value = ''
        for line, text in self.__lines:
            option_value += text
        self.section.options[self.name] = Option(
            self.name, option_value,
            format_location(self.__filename, self.__start_line, line),
            self.section)


class SectionParser(object):
    """Temporary object used to parse a section.
    """

    def __init__(self, name, configuration, filename, line):
        self.name = name
        self.configuration = configuration
        self.__filename = filename
        self.__start_line = line
        self.__lines = []

    @classmethod
    def new_section(klass, configuration, text, filename, line):
        is_header = SECTION_HEADER.match(text)
        if is_header:
            return klass(
                is_header.group('header'), configuration, filename, line)
        return None

    def add(self, line, text):
        self.__lines.append((line, text,))

    def done(self, line):
        location = format_location(self.__filename, self.__start_line, line)
        section = Section(self.name, location, self.configuration)
        option = None

        for line_number, text in self.__lines:
            new_option = OptionParser.new_option(
                section, text, self.__filename, line_number)
            if new_option is not None:
                if option is not None:
                    option.done(line_number - 1)
                option = new_option
            else:
                if option is not None:
                    option.add(line, text)
                else:
                    raise ConfigurationError(
                        location,
                        u'garbage text before option at line %s' % line_number)
        if option is not None:
            option.done(line_number)

        self.configuration.sections[self.name] = section


marker = object()


class Configuration(object):
    """Configuration.
    """

    def __init__(self, location):
        self.__location = location
        self.sections = {}

    def get_cfg_directory(self):
        """Return the directory where the config file resides.
        """
        return os.path.dirname(self.__location)

    @classmethod
    def read(klass, uri):
        """Read a configuration file located at the given uri.
        """
        input = open_uri(uri)
        try:
            return klass.read_lines(input.readlines, uri)
        finally:
            input.close()

    @classmethod
    def read_lines(klass, lines, origin):
        """Read a configuration from the given string, that would be
        refered by origin.
        """
        configuration = klass(origin)
        line_number = 0
        section = None

        for text in lines():
            line_number += 1
            # Comment
            if not text.strip() or text[0] in '#;':
                continue

            # Some sources gives '\n' at the end of the lines, someother don't
            text = text.rstrip()

            # New section
            new_section = SectionParser.new_section(
                configuration, text, origin, line_number)
            if new_section is not None:
                if section is not None:
                    section.done(line_number - 1)
                section = new_section
            else:
                if section is not None:
                    section.add(line_number, text)
                else:
                    raise ConfigurationError(
                        origin,
                        u'Garbage text before section at line %d' % line_number)

        if section is not None:
            section.done(line_number)
        else:
            raise ConfigurationError(origin, u'No section defined')
        return configuration

    def write(self, stream):
        """Serialize the configuration on the stream in a readable format.
        """
        section_names = self.sections.keys()
        section_names.sort()
        for name in section_names:
            self.sections[name]._write(stream)
            stream.write('\n')

    def __copy__(self):
        new_conf = self.__class__(self.__location)
        for section_name in self.sections.keys():
            new_conf[section_name] = self.sections[section_name]
        return new_conf

    def __add__(self, other):
        if not isinstance(other, Configuration):
            raise ValueError(u'Can only add two configuration together')

        # Create a copy of this configuration
        new_conf = self.__copy__()

        # Add of update sections with ones comimng from other.
        for section_name in other.sections.keys():
            if section_name not in new_conf:
                new_conf[section_name] = other.sections[section_name]
            else:
                new_conf[section_name] += other.sections[section_name]
        return new_conf

    def __getitem__(self, key, default=marker):
        try:
            return self.sections[key]
        except KeyError:
            if default is not marker:
                return default
            raise ConfigurationError(
                self.__location, u'Missing %s section' % key)

    get = __getitem__

    def __setitem__(self, key, value):
        if not isinstance(value, Section):
            raise ValueError(u'Can only add section to a configuration')
        section = value.__copy__()
        section.configuration = self
        self.sections[key] = section

    def __contains__(self, key):
        return self.sections.__contains__(key)

    def items(self):
        """Iter on sections.
        """
        return self.sections.iteritems()


class Section(object):
    """Section of a configuration file.
    """

    def __init__(self, name, location=None, configuration=None):
        self.name = name
        self.configuration = configuration
        self.__location = location
        self.options = {}

    def __copy__(self):
        new_section = self.__class__(self.name, location=self.__location)
        for option_name in self.options.keys():
            new_section[option_name] = self.options[option_name]
        return new_section

    def __add__(self, other):
        if not isinstance(other, Section):
            raise ValueError(u'Can only add two sections together')

        # Create a copy of this section
        new_section = self.__copy__()

        # Update with other options if empty
        for option_name in other.options.keys():
            if option_name not in new_section:
                new_section[option_name] = other.options[option_name]
        return new_section

    def __getitem__(self, key, default=marker):
        try:
            return self.options[key]
        except KeyError:
            if default is not marker:
                if isinstance(default, str):
                    return Option('default', default)
                return default
            raise ConfigurationError(
                self.__location,
                u'Missing option %s in section %s' % (key, self.name))

    get = __getitem__

    def __setitem__(self, key, value):
        if isinstance(value, list) or isinstance(value, tuple):
            value = '\n    '.join(value)
        if isinstance(value, str):
            if key in self.options:
                # XXX Not sure we want do to that
                self.options[key].set_value(value)
            else:
                self.options[key] = Option(
                    key, value, section=self)
        elif isinstance(value, Option):
            option = value.__copy__()
            option.section = self
            self.options[key] = option
        else:
            raise ValueError(u'Can only use string')

    def __contains__(self, key):
        return self.options.__contains__(key)

    def items(self):
        """Iter on options.
        """
        return self.options.iteritems()

    def _write(self, stream):
        stream.write('[' + self.name + ']\n')
        option_names = self.options.keys()
        option_names.sort()
        for name in option_names:
            self.options[name]._write(stream)

    def as_dict(self):
        """Return the content of the section as a dictionnary.
        """
        return dict([(key, self.options[key].as_text())
                     for key in self.options.keys()])


class Option(object):
    """Option in a section.
    """

    def __init__(self, name, value, location=None, section=None):
        self.name = name
        self.section = section
        self.__location = location
        self.__value = value
        self.__access_callbacks = []

    def __copy__(self):
        return self.__class__(self.name, self.__value, location=self.__location)

    def __get_value(self):
        # XXX Should cache this
        value = self.__value
        replace = OPTION_REPLACE.search(value)
        while replace:
            section_name = replace.group('section')
            if section_name:
                section = self.section.configuration[section_name]
            else:
                section = self.section
            option_value = section[replace.group('option')].as_text()
            value = value[0:replace.start()] + \
                option_value + \
                value[replace.end():]
            replace = OPTION_REPLACE.search(value)
        for callback in self.__access_callbacks:
            callback(value)
        return value

    def set_value(self, value):
        """Set the value of the option.
        """
        self.__value = value

    def register(self, func):
        self.__access_callbacks.append(func)

    def _write(self, stream):
        stream.write(self.name + ' = ' + self.__value)
        if not self.__value or self.__value[-1] != '\n':
            stream.write('\n')

    def as_text(self):
        """Return the value as plain raw text.
        """
        return self.__get_value().strip()

    def as_bool(self):
        value = self.__get_value()
        bool = value.lower()
        if bool in ('on', 'true', '1',):
            return True
        if bool in ('off', 'false', '0',):
            return False
        raise ConfigurationError(
            self.__location,
            u'option %s is not a boolean: %s' % (self.name, value))

    def as_int(self):
        """Return the value as an integer.
        """
        value = self.__get_value()
        try:
            return int(value)
        except ValueError:
            raise ConfigurationError(
                self.__location,
                u'option %s is not an integer: %s' % (self.name, value))

    def as_list(self):
        """Return the value's lines as a list.
        """
        return filter(lambda s: len(s),
                      map(lambda s: s.strip(),
                          self.__get_value().split('\n')))

    def as_words(self):
        """Return value as a list of word. You can wrap a word with a
        pair of " to escape spaces in it, or you can use \ just before
        (to write " write \", for \ write \\).
        """
        words = []
        word = ""
        is_escaped = False
        is_previous_backslash = False
        for letter in self.__get_value():
            if letter == '\\':
                if not is_previous_backslash:
                    is_previous_backslash = True
                    continue
            if not is_previous_backslash and letter == '"':
                is_escaped = not is_escaped
                continue
            if (not is_escaped and
                not is_previous_backslash and
                letter.isspace()):
                if word:
                    words.append(word)
                    word = ""
                continue
            word += letter
            is_previous_backslash = False
        if is_escaped or is_previous_backslash:
            raise ConfigurationError(
                self.__location,
                u"malformed last word for option %s" % self.name)
        if word:
            words.append(word)
        return words
