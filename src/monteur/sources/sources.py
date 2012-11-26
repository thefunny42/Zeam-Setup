
import bisect
import logging
import operator
import os

from monteur.distribution.workingset import working_set
from monteur.error import ConfigurationError, PackageNotFound
from monteur.error import InstallationError
from monteur.version import Requirement

logger = logging.getLogger('monteur')


STRATEGY_QUICK = 'quick'
STRATEGY_UPDATE = 'update'


class PackageInstallers(object):
    """A release group group releases for the same software (key)
    """

    def __init__(self, key, installers=None):
        self.key = key
        if installers is None:
           installers = []
        self.installers = installers
        assert isinstance(self.installers, list), u"Installers must be a list"
        self.installers.sort()

    def add(self, installer):
        """Add an installer to the set of available ones.
        """
        if installer.key != self.key:
            raise InstallationError(u'Invalid installer added to set.')
        bisect.insort(self.installers, installer)

    def extend(self, installers):
        """Extend set with an set of available installers.
        """
        if installers:
            assert isinstance(installers, PackageInstallers)
            if installers.key != self.key:
                raise InstallationError(u'Invalid installer added to set.')
            for installer in installers:
                bisect.insort(self.installers, installer)

    def remove(self, installer):
        """Remove a given installer from the set.
        """
        if installer.key == self.key:
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
            self.key, filter(installers_filter, self.installers))

    def __getitem__(self, requirement):
        if not isinstance(requirement, Requirement):
            raise KeyError(requirement)
        return self.get_installers_for(requirement)

    def __iter__(self):
        return iter(self.installers)

    def __len__(self):
        return len(self.installers)

    def __repr__(self):
        return '<PackageInstallers %s>' % self.key


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
        default = PackageInstallers(installer.key)
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

    def get_installers_for(self, requirement, pyversion=None, platform=None):
        if not requirement.key in self.installers:
            return []
        return self.installers[requirement.key].get_installers_for(
            requirement, pyversion=pyversion, platform=platform)

    def __len__(self):
        return len(self.installers)

    def __iter__(self):
        return iter(self.installers)

    def __getitem__(self, key):
        if isinstance(key, Requirement):
            return self.installers[key.key][key]
        return self.installers[key]

    def __contains__(self, key):
        if isinstance(key, Requirement):
            return key.key in self.installers
        return key in self.installers

    def __repr__(self):
        return '<Installers %s>' % self.key


class Query(object):
    """Query a set of installers for a given requirement.
    """

    def __init__(self, context, installers):
        self.installers = installers
        self.pyversion = context.pyversion
        self.platform = context.platform

    def __call__(self, requirement, strategy):
        return self.installers.get_installers_for(
            requirement, self.pyversion, self.platform)


class QueryContext(object):
    """Contains the context used to query a package source.
    """

    def __init__(self, source, interpretor, path, priority, trust=0):
        """Create a new context object for source. Packages will be
        installed for the given interpretor in the given path.
        """
        self.path = path
        self.interpretor = interpretor
        self.pyversion = interpretor.get_version()
        self.platform = interpretor.get_platform()
        self.releases = source.options.utilities.releases
        self.priority = priority
        self.trust = trust

    def load(self, distribution):
        """Load distribution metadata.
        """
        return self.releases.load(
            distribution,
            distribution.path,
            self.interpretor,
            trust=self.trust)

    def get_install_path(self, distribution):
        """Return the installation path for the given distribution.
        """
        return os.path.join(
            self.path,
            distribution.get_egg_directory(self.interpretor))


class Source(object):
    """Base class for source.
    """
    Context = QueryContext
    TRUST = -99

    def __init__(self, options, installed_options=None):
        self.options = options
        self.installed_options = installed_options

    def is_uptodate(self):
        if self.installed_options is None:
            return True
        return (self.options == self.installed_options)

    def create(self, interpretor, path, priority):
        """Create a context object for a query. Context object
        contains the required information for the query and package
        installers to work.
        """
        return self.Context(self, interpretor, path, priority, self.TRUST)

    def prepare(self, context):
        """Prepare a query object from a context. You can use the
        query object to find packages.
        """
        raise NotImplementedError

    def __repr__(self):
        return '<%s>' % (self.__class__.__name__)


class Queries(object):
    """Used to query instance of sources for a package.
    """

    def __init__(self, queries):
        self.queries = queries

    def __call__(self, requirement, strategy=STRATEGY_UPDATE):
        """Search of a given package at the given location.
        """
        unique = requirement.is_unique()
        candidates = PackageInstallers(requirement.key)
        for query in self.queries:
            candidates.extend(query(requirement, strategy))
            if unique and candidates:
                return candidates
        if candidates:
            return candidates
        raise PackageNotFound(repr(requirement))


class Sources(object):
    """This manage software sources.
    """

    def __init__(self, configuration, section_name='setup'):
        __status__ = u"Initializing software sources."
        self.sources = []
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
            self.sources.append(
                factory(
                    options,
                    self.installed.get('source:' + name, None)))
        self._uptodate = None

    def is_uptodate(self):
        """Return True if the configuration for sources didn't change
        between the current and installed configuration.
        """
        if self._uptodate is None:
            self._uptodate = reduce(
                operator.and_,
                map(lambda s: s.is_uptodate(),
                    self.sources))
        return self._uptodate

    def __call__(self, interpretor, path):
        """Return an object Queries that can be used to lookup
        packages to install.
        """
        queries = []
        for priority, source in enumerate(self.sources):
            query = source.prepare(source.create(interpretor, path, priority))
            if query is None:
                continue
            queries.append(query)
        return Queries(queries)

    def __repr__(self):
        return '<Source %s>' % ', '.join(map(repr, self.sources))

