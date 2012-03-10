
import re
import os

from zeam.setup.base.configuration.option import Option, OptionParser
from zeam.setup.base.error import ConfigurationError
from zeam.setup.base.utils import format_line

SECTION_HEADER = re.compile(r'\[(?P<header>[^]]+)\]')
marker = object()


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

    def __eq__(self, other):
        if not isinstance(other, Section):
            return NotImplemented
        local_options = set(self.options.keys())
        other_options = set(other.options.keys())
        if local_options != other_options:
            return False
        for name in local_options:
            if self.options[name] != other.options[name]:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def items(self):
        """Iter on options.
        """
        return self.options.iteritems()

    def keys(self):
        """All options keys.
        """
        return self.options.keys()

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
