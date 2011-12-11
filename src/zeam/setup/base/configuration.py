
import os
import re
import logging

from zeam.setup.base.error import ConfigurationError
from zeam.setup.base.utils import open_uri, relative_uri

logger = logging.getLogger('zeam.setup')


SECTION_HEADER = re.compile(r'\[(?P<header>[^]]+)\]')
OPTION_HEADER = re.compile(
    r'(?P<option>[^=\s]+)\s*(?P<operator>[\+\-]?=)\s*(?P<value>.*)$')
OPTION_REPLACE = re.compile(
    r'\$\{(?P<section>[^:]*):(?P<option>[^\}]+)\}')


def as_list(value):
    """Return the given value as a list.
    """
    return filter(lambda s: len(s),
                  map(lambda s: s.strip(),
                      value.split('\n')))



def format_line(start_line, end_line=None):
    """Format location information to report it.
    """
    location = u'line %d' % (start_line)
    if end_line is not None and end_line != start_line:
        location += u' to %d' % end_line
    return location


class OptionParser(object):
    """Temporary object used to parse an option.
    """

    def __init__(self, name, text, section, filename, line, operator):
        self.name = name
        self.section = section
        self._filename = filename
        self._start_line = line
        self._lines = [(line, text + '\n',)]
        self._operator = operator

    @classmethod
    def new_option(klass, section, text, filename, line):
        is_header = OPTION_HEADER.match(text)
        if is_header:
            return klass(
                is_header.group('option'),
                is_header.group('value'),
                section,
                filename,
                line,
                is_header.group('operator'))
        return None

    def add(self, line, text):
        self._lines.append((line, text + '\n',))

    def done(self, line):
        if line == self._start_line:
            line = None
        option_value = ''
        for line, text in self._lines:
            option_value += text
        self.section.options[self.name] = Option(
            self.name, option_value,
            location=(self._filename, format_line(self._start_line, line)),
            section=self.section,
            operator=self._operator)


class SectionParser(object):
    """Temporary object used to parse a section.
    """

    def __init__(self, name, configuration, filename, line):
        self.name = name
        self.configuration = configuration
        self._filename = filename
        self._start_line = line
        self._lines = []

    @classmethod
    def new_section(klass, configuration, text, filename, line):
        is_header = SECTION_HEADER.match(text)
        if is_header:
            return klass(
                is_header.group('header'), configuration, filename, line)
        return None

    def add(self, line, text):
        self._lines.append((line, text,))

    def done(self, line):
        location = (self._filename, format_line(self._start_line, line))
        section = Section(
            self.name,
            location=location,
            configuration=self.configuration)
        option = None

        for line_number, text in self._lines:
            new_option = OptionParser.new_option(
                section, text, self._filename, line_number)
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


class Utilities(object):
    """Utility registry.
    """

    def __init__(self, configuration):
        self._configuration = configuration
        self._utilities = {}
        self._factories = {}

    def register(self, name, factory):
        self._factories[name] = factory

    def __getattr__(self, key):
        if key in self._utilities:
            return self._utilities[key]
        if key in self._factories:
            utility = self._factories[key](self._configuration)
            self._utilities[key] = utility
            return utility
        raise AttributeError(key)


class ConfigurationDiffUtility(object):
    """Utlity to trace changes between two different configurations.
    """

    def __init__(self, configuration):
        self._configuration = configuration

    def get_option_changes(self, section):
        """Return a tuple (added, changed, removed) indicating the
        mutation in a section.
        """
        section_name = section.name
        if section_name not in self._configuration:
            return (section, None)

    def get_option_values_changes(self, option):
        """Return a tuple (added, removed) of values changes. Order of
        items are preserved.
        """
        assert isinstance(option, Option)
        option_name = option.name
        section_name = option.section.name
        if section_name not in self._configration:
            # Section was not here, everything is new
            return (option.as_list(), None)
        previous_section = self._configuraction[section_name]
        if option_name not in previous_section:
            # Option was not here, everything is new
            return (option.as_list(), None)
        previous_option = previous_section[option_name]
        values = option.as_list()
        previous_values = previous_option.as_list()
        added = []
        removed = []
        for value in values:
            if value not in previous_values:
                added.append(value)
        for value in previous_values:
            if value not in values:
                removed.append(value)
        return (added, removed)


class Configuration(object):
    """Configuration.
    """
    default_section = 'setup'

    def __init__(self, location=None):
        self._location = location
        self.sections = {}
        self.utilities = Utilities(self)

    def get_cfg_directory(self):
        """Return the directory where the config file resides.
        """
        if self._location:
            return os.path.dirname(self._location)
        return None

    @classmethod
    def read(cls, uri):
        """Read a configuration file located at the given uri.
        """
        input = open_uri(uri)
        try:
            return cls.read_lines(input.readlines, uri)
        finally:
            input.close()

    @classmethod
    def read_lines(cls, lines, origin):
        """Read a configuration from the given string, that would be
        refered by origin.
        """
        configuration = cls(origin)
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

        # Support online include to extend configuration
        if cls.default_section in configuration:
            section = configuration[cls.default_section]
            if 'extends' in section:
                for uri in section['extends'].as_list():
                    configuration += Configuration.read(
                        relative_uri(origin, uri))
                    del configuration[cls.default_section]['extends']
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
        new_conf = self.__class__(self._location)
        for section_name in self.sections.keys():
            new_conf[section_name] = self.sections[section_name]
        return new_conf

    def __add__(self, other):
        if not isinstance(other, Configuration):
            raise TypeError(u'Can only add two configuration together.')

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
                self._location,
                u'Missing %s section.' % key)

    get = __getitem__

    def __setitem__(self, key, value):
        if not isinstance(value, Section):
            raise TypeError(u'Can only add section to a configuration.')
        if value.configuration is not self:
            value = value.__copy__()
            value.configuration = self
        self.sections[key] = value

    def __delitem__(self, key):
        del self.sections[key]

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
        self._location = location
        self.options = {}

    @property
    def utilities(self):
        return self.configuration.utilities

    @property
    def location(self):
        if self._location:
            return ': '.join(self._location)
        return None

    def get_cfg_directory(self):
        """Return the directory where the config file what contains
        this section resides.
        """
        if self._location:
            return os.path.dirname(self._location[0])
        return None

    def __copy__(self):
        new_section = self.__class__(self.name, location=self._location)
        for option_name in self.options.keys():
            new_section[option_name] = self.options[option_name]
        return new_section

    def __add__(self, other):
        if not isinstance(other, Section):
            raise TypeError(u'Can only add two sections together.')

        # Create a copy of this section
        new_section = self.__copy__()

        # Update with other options if empty
        for option_name in other.options.keys():
            if option_name not in new_section:
                new_section[option_name] = other.options[option_name]
            else:
                new_section[option_name] += other.options[option_name]
        return new_section

    def __getitem__(self, key, default=marker):
        try:
            return self.options[key]
        except KeyError:
            if default is not marker:
                if isinstance(default, str):
                    return Option('default', default, section=self)
                return default
            raise ConfigurationError(
                self.location,
                u'Missing option %s in section %s.' % (key, self.name))

    get = __getitem__

    def get_with_default(self, key, default_section, default=marker):
        if key in self.options:
            return self.options[key]
        return self.configuration[default_section].get(key, default=default)

    def __setitem__(self, key, value):
        if isinstance(value, Option):
            if value.section is not self:
                value = value.__copy__()
                value.section = self
            self.options[key] = value
        elif key in self.options:
            self.options[key].set_value(value)
        else:
            self.options[key] = Option(key, value, section=self)

    def __delitem__(self, key):
        del self.options[key]

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

    def __init__(self, name, value, location=None, section=None, operator='='):
        self.name = name
        self.section = section
        self.set_value(value)
        self._location = location
        self._add_value = ''
        self._remove_value = ''
        if operator == '+=':
            self._add_value = self._value
        elif operator == '-=':
            self._remove_value = self._value
            self._value = ''
        self._callbacks = []

    @property
    def location(self):
        if self._location:
            return ': '.join(self._location)
        return None

    def get_cfg_directory(self):
        """Return the directory where the config file what contains
        this section resides.
        """
        if self._location:
            return os.path.dirname(self._location[0])
        return None

    def __copy__(self):
        copy = self.__class__(self.name, self._value, location=self._location)
        if self._add_value:
            copy._add_value = str(self._add_value)
        if self._remove_value:
            copy.remove_value = str(self._remove_value)
        return copy

    def __add__(self, other):
        if not isinstance(other, Option):
            raise TypeError(u"Can only add two options together")
        if self._add_value or self._remove_value:
            value = as_list(other._value)
            if self._add_value:
                value.extend(as_list(self._add_value))
            if self._remove_value:
                removed = set(as_list(self._remove_value))
                value = filter(lambda v: v not in removed, value)
        else:
            value = self._value
        return self.__class__(self.name, value, location=self._location)

    def get_value(self):
        """Return the computed value of the option interpreted.
        """
        if self._computed_value is not None:
            return self._computed_value
        value = self._value
        replace = OPTION_REPLACE.search(value)
        while replace:
            section_name = replace.group('section')
            if section_name:
                section = self.section.configuration[section_name]
            else:
                section = self.section
            option_value = section[replace.group('option')].as_text()
            value = ''.join((value[0:replace.start()],
                             option_value,
                             value[replace.end():]))
            replace = OPTION_REPLACE.search(value)
        for callback in self._callbacks:
            callback(value)
        self._computed_value = value
        return value

    def set_value(self, value):
        """Set the value of the option.
        """
        if isinstance(value, list) or isinstance(value, tuple):
            value = '\n    ' + '\n    '.join(value)
        elif isinstance(value, bool):
            if value:
                value = 'on'
            else:
                value = 'off'
        elif isinstance(value, int):
            value = str(value)
        if not isinstance(value, basestring):
            raise ValueError(u"Can only set strings as value.")
        self._value = value
        self._computed_value = None

    def register(self, func):
        self._callbacks.append(func)

    def _write(self, stream):
        stream.write(self.name + ' = ' + self._value)
        if not self._value or self._value[-1] != '\n':
            stream.write('\n')

    def as_text(self):
        """Return the value as plain raw text.
        """
        return self.get_value().strip()

    def as_bool(self):
        value = self.get_value().strip()
        bool = value.lower()
        if bool in ('on', 'true', '1',):
            return True
        if bool in ('off', 'false', '0',):
            return False
        raise ConfigurationError(
            self.location,
            u'option %s is not a boolean: %s' % (self.name, value))

    def as_int(self):
        """Return the value as an integer.
        """
        value = self.get_value()
        try:
            return int(value)
        except ValueError:
            raise ConfigurationError(
                self.location,
                u'option %s is not an integer: %s' % (self.name, value))

    def as_list(self):
        """Return the value's lines as a list.
        """
        return as_list(self.get_value())

    def as_words(self):
        """Return value as a list of word. You can wrap a word with a
        pair of " to escape spaces in it, or you can use \ just before
        (to write " write \", for \ write \\).
        """
        words = []
        word = ""
        is_escaped = False
        is_previous_backslash = False
        for letter in self.get_value():
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
                self.location,
                u"malformed last word for option %s" % self.name)
        if word:
            words.append(word)
        return words
