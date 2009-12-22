
import os
import re

from zeam.setup.base.error import ConfigurationError
from zeam.setup.base.utils import open_uri


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
        self.__lines = [(line, text,)]

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
        self.__lines.append((line, text,))

    def done(self, line):
        # XXX Review this
        if line == self.__start_line:
            line = None
        option_value = ''
        for line, text in self.__lines:
            option_value += text + '\n'
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
                        'Garbage text before option at line %s' % line_number)
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

    @classmethod
    def read(klass, filename):
        input = open_uri(filename)
        configuration = klass(filename)
        line_number = 0
        section = None

        for text in input.readlines():
            line_number += 1
            # Comment
            if not text.strip() or text[0] in '#;':
                continue

            # New section
            new_section = SectionParser.new_section(
                configuration, text, filename, line_number)
            if new_section is not None:
                if section is not None:
                    section.done(line_number - 1)
                section = new_section
            else:
                if section is not None:
                    section.add(line_number, text)
                else:
                    raise ConfigurationError(
                        filename,
                        'Garbage text before section at line %d' % line_number)
        input.close()
        if section is not None:
            section.done(line_number)
        else:
            raise ConfigurationError(filename, 'No section defined')
        return configuration

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


class Section(object):
    """Section of a configuration file.
    """

    def __init__(self, name, location, configuration=None):
        self.name = name
        self.configuration = configuration
        self.__location = location
        self.options = {}

    def __copy__(self):
        new_section = self.__class__(self.name, self.__location)
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
                    return Option('default', default, 'default-value')
                return default
            raise ConfigurationError(
                self.__location,
                u'Missing option %s in section %s' % (key, self.name))

    get = __getitem__

    def __setitem__(self, key, value):
        if isinstance(value, str):
            if key in self.options:
                # XXX Not sure we want do to that
                self.options[key].set_value(value)
            else:
                self.options[key] = Option(
                    key, value, u'dynamic add-on', self)
        elif isinstance(value, Option):
            option = value.__copy__()
            option.section = self
            self.options[key] = option
        else:
            raise ValueError(u'Can only use string')

    def __contains__(self, key):
        return self.options.__contains__(key)

    def as_dict(self):
        return dict([(key, self.options[key].as_text())
                     for key in self.options.keys()])


class Option(object):
    """Option in a section.
    """

    def __init__(self, name, value, location, section=None):
        self.name = name
        self.section = section
        self.__location = location
        self.__value = value
        self.__access_callbacks = []

    def __copy__(self):
        return self.__class__(self.name, self.__value, self.__location)

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
        self.__value = value

    def register(self, func):
        self.__access_callbacks.append(func)

    def as_text(self):
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
        value = self.__get_value()
        try:
            return int(value)
        except ValueError:
            raise ConfigurationError(
                self.__location,
                u'option %s is not an integer: %s' % (self.name, value))

    def as_list(self):
        return filter(lambda s: len(s),
                      map(lambda s: s.strip(),
                          self.__get_value().split('\n')))
