
import bisect
import logging
import operator

from zeam.setup.base.distribution.workingset import working_set
from zeam.setup.base.error import ConfigurationError, PackageNotFound
from zeam.setup.base.error import InstallationError
from zeam.setup.base.version import Requirement

logger = logging.getLogger('zeam.setup')


class PackageInstallers(object):
    """A release group group releases for the same software (name)
    """

    def __init__(self, name, installers=None):
        self.name = name
        if installers is None:
           installers = []
        self.installers = installers
        assert isinstance(self.installers, list), u"Installers must be a list"
        self.installers.sort()

    def add(self, installer):
        if installer.name != self.name:
            raise InstallationError(u'Invalid installer added to collection')
        bisect.insort(self.installers, installer)

    def remove(self, installer):
        if installer.name == self.name:
            if installer in self.installers:
                self.installers.remove(installer)

    def get_most_recent(self):
        """Return the most recent installer.
        """
        # Since self.installers is sorted it should be the last one
        return self.installers and self.installers[-1] or None

    def get_installers_for(self, requirement, pyversion=None, platform=None):
        """Filter out installers that doesn't match the criterias.
        """

        def installers_filter(installer):
            return installer.filter(requirement, pyversion, platform)

        return self.__class__(
            self.name, filter(installers_filter, self.installers))

    def __getitem__(self, requirement):
        if not isinstance(requirement, Requirement):
            raise KeyError(requirement)
        return self.get_installers_for(requirement)

    def __len__(self):
        return len(self.installers)

    def __repr__(self):
        return '<Software %s>' % self.name


class Installers(object):
    """Represent the available software.
    """

    def __init__(self, installers=[]):
        self.installers = {}
        for installer in installers:
            self.add(installer)

    def add(self, installer):
        """Add a software to the available ones.
        """
        default = PackageInstallers(installer.name)
        self.installers.setdefault(installer.key, default).add(installer)

    def extend(self, installers):
        """Extend the available software by adding a list of installers to it.
        """
        for installer in installers:
            self.add(installer)

    def remove(self, installer):
        """Remove an installer from the collection.
        """
        if installer.key in self.installers:
            self.installers[installer.key].remove(installer)

    def __len__(self):
        return len(self.installers)

    def __getitem__(self, key):
        if isinstance(key, Requirement):
            return self.installers[key.key][key]
        return self.installer[key]

    def get_installers_for(self, requirement, pyversion=None, platform=None):
        if not requirement.key in self.installers:
            return []
        return self.installers[requirement.key].get_installers_for(
            requirement, pyversion=pyversion, platform=platform)


class Source(object):
    """Base class for source.
    """

    def __init__(self, options, installed_options=None):
        self.options = options
        self.installed_options = installed_options

    def is_uptodate(self):
        if self.installed_options is None:
            return True
        return (self.options == self.installed_options)

    def initialize(self, first_time):
        pass

    def available(self, configuration):
        return True

    def search(self, requirement, interpretor):
        raise NotImplementedError

    def __repr__(self):
        return '<%s>' % (self.__class__.__name__)


class Sources(object):
    """This manage software sources.
    """

    def __init__(self, configuration, section_name='setup'):
        __status__ = u"Initializing software sources."
        self.sources = []
        self.available_sources = []
        self.configuration = configuration
        self.installed = configuration.utilities.installed

        defined_sources = working_set.list_entry_points('setup_sources')
        for name in configuration[section_name]['sources'].as_list():
            options = configuration['source:' + name]
            source_type = options['type'].as_text()
            if source_type not in defined_sources:
                raise ConfigurationError(
                    u'Unknow source type %s for %s' % (
                        source_type, name))
            factory = working_set.get_entry_point(
                'setup_sources',
                defined_sources[source_type]['name'])
            self.sources.append(factory(
                    options,
                    self.installed.get('source:' + name, None)))
        self._initialized = False
        self._uptodate = None

    def is_uptodate(self):
        if self._uptodate is None:
            self._uptodate = reduce(
                operator.and_,
                map(lambda s: s.is_uptodate(),
                    self.sources))
        return self._uptodate

    def initialize(self):
        if self._initialized:
            for source in self.available_sources:
                source.initialize(False)
            return
        for source in self.sources:
            if not source.available(self.configuration):
                continue
            source.initialize(True)
            self.available_sources.append(source)
        self._initialized = True

    def search(self, requirement, interpretor):
        """Search of a given package at the given location.
        """
        for source in self.available_sources:
            try:
                return source.search(requirement, interpretor)
            except PackageNotFound:
                continue
        raise PackageNotFound(repr(requirement))

    def __repr__(self):
        return '<Source %s>' % ', '.join(map(repr, self.sources))

