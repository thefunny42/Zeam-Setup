
import os
import shlex
import re

from monteur.error import ConfigurationError
from monteur.utils import format_line, relative_uri, create_directory

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

    def __eq__(self, other):
        if not isinstance(other, Option):
            return NotImplemented
        return set(self.as_list()) == set(other.as_list())

    def __ne__(self, other):
        return not self.__eq__(other)

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

    def as_directory(self):
        """Return the value as a directory, creating it if needed.
        """
        return create_directory(self.as_text())

    def as_file(self):
        """Return the value as a file, relative to the configuration
        one where the option is defined.
        """
        origin = self.get_cfg_directory()
        return relative_uri(origin, self.as_text(), True)

    def as_files(self):
        """Return the value as a list of files, relative to the
        configuration one where the option is defined.
        """
        origin = self.get_cfg_directory()
        return map(lambda uri: relative_uri(origin, uri, True), self.as_list())

    def as_words(self):
        """Return value as a list of word. You can wrap a word with a
        pair of " to escape spaces in it, or you can use \ just before
        (to write " write \", for \ write \\).
        """
        value = self.get_value()
        try:
            return shlex.split(value)
        except ValueError:
            raise ConfigurationError(
                self.location,
                u"malformed last word for option %s" % self.name)

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

