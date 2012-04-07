
import os
import logging

from zeam.setup.base.configuration.section import SectionParser, Section
from zeam.setup.base.configuration.utilities import Utilities
from zeam.setup.base.error import ConfigurationError
from zeam.setup.base.utils import open_uri, relative_uri, absolute_uri

logger = logging.getLogger('zeam.setup')
marker = object()


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
        abs_uri = absolute_uri(uri)
        input = open_uri(abs_uri)
        try:
            return cls.read_lines(input.readlines, abs_uri)
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

    def __iter__(self):
        return self.sections.itervalues()

    def items(self):
        """Iter on sections.
        """
        return self.sections.iteritems()

    def keys(self):
        """All section names.
        """
        return self.sections.keys()

    def values(self):
        """All sections values.
        """
        return self.sections.values()
