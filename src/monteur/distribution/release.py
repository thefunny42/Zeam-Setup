
import logging
import sys
from distutils.util import get_platform

from monteur.distribution.loader import SetupLoader
from monteur.error import PackageError, InstallationError
from monteur.error import ConfigurationError
from monteur.version import Version

logger = logging.getLogger('monteur')


class Release(object):
    """Represent a release of a software.
    """

    def __init__(self, name=None, version=None, path=None,
                 pyversion=None, platform=None, url=None,
                 format=None, package_path=None):
        self.name = name
        self.version = Version.parse(version)
        self.summary = ''
        self.author = ''
        self.author_email = ''
        self.license = ''
        self.classifiers = []
        self.format = format
        self.url = url
        self.pyversion = pyversion
        self.platform = platform
        self.path = path
        self.package_path = package_path or path
        self.entry_points = {}
        self.requirements = []
        self.extras = {}
        self.extensions = []

    @apply
    def name():
        # Write a property for name, in order to set key.
        def getter(self):
            return self._name
        def setter(self, name):
            self._name = name
            self.key = name and name.lower().replace('-', '_') or None
        return property(getter, setter)

    def __lt__(self, other):
        return self.version < other

    def __gt__(self, other):
        return self.version > other

    def __eq__(self, other):
        return self.version == other

    def is_active(self):
        """Return true of the release is currently usable by the
        current process.
        """
        return self.path in sys.path

    def activate(self):
        """Activate the release in the current process.
        """
        if self.path is None:
            raise InstallationError(
                self.name, u'Trying to activate a non-installed package')
        if self.is_active():
            return
        # XXX Should only do it if the interpreter is the same
        sys.path.insert(len(sys.path) and 1 or 0, self.path)

    def get_egg_directory(self, interpretor):
        """Return a directory name suitable to store the egg,
        compatible with setuptools format.
        """
        interpretor_pyversion = interpretor.get_version()
        if self.pyversion is not None:
            if self.pyversion != interpretor_pyversion:
                raise PackageError(
                    u"Package %s requires Python %s is used with %s" % (
                        self.name, self.pyversion, interpretor_pyversion))
        items = [self.name.replace('-', '_'),
                 str(self.version),
                 'py%s' % (self.pyversion or interpretor_pyversion)]
        if self.extensions:
            items.append(get_platform())
        return '-'.join(items) + '.egg'

    def _load(self, entry_point, group, name):
        # Private helper to load an entry point.
        parts = entry_point.split(':')
        if len(parts) != 2:
            raise PackageError(u"Invalid entry point '%s' for package %s" % (
                    entry_point, self.name))
        python_path, attribute = parts
        try:
            python_module = __import__(
                python_path, globals(), globals(), [attribute])
        except ImportError, error:
            raise PackageError(
                self.name,
                u'Invalid module %s for entry point %s %s:%s.' % (
                    python_path, group, self.name, name),
                detail=str(error))
        try:
            python_value = getattr(python_module, attribute)
        except AttributeError:
            raise PackageError(
                self.name,
                u'Invalid attribute %s in module %s ' \
                    'for entry point %s %s:%s.' % (
                    attribute, python_path, group, self.name, name))
        return python_value

    def get_entry_point(self, group, name):
        """Load the entry point called name in the given group and return it.
        """
        if group not in self.entry_points:
            return None
        if name not in self.entry_points[group]:
            return None

        # Activate plugin if needed
        if not self.is_active():
            self.activate()

        # Load the entry point
        return self._load(self.entry_points[group][name], group, name)

    def iter_all_entry_points(self, group):
        """Load all entry points in the given group and return them.
        """
        if group in self.entry_points:
            # Activate plugin if needed
            if not self.is_active():
                self.activate()

            for name, entry_point in self.entry_points[group].iteritems():
                yield (name, self._load(entry_point, group, name))

    def __str__(self):
        return '%s == %s' % (self.name, self.version)

    def __repr__(self):
        return '<%s for %s version %s>' % (
            self.__class__.__name__, self.name, self.version)


def current_package(configuration):
    loader = SetupLoader(configuration, Release())
    return loader.load()


class Loaders(object):
    CONFIG_KEY = 'setup_loaders'

    def __init__(self, configuration):
        from monteur.distribution.workingset import working_set

        self.loaders = []
        names = configuration['setup'].get(
            self.CONFIG_KEY, 'egg,monteur').as_list()
        defined_loaders = working_set.list_entry_points('setup_loaders')
        for name in names:
            if name not in defined_loaders:
                raise ConfigurationError(u'Undefined setup loader', name)
            factory = working_set.get_entry_point(
                'setup_loaders', defined_loaders[name]['name'])
            if factory is not None:
                self.loaders.append(factory(configuration.get(
                            ':'.join((self.CONFIG_KEY, name)), None)))

    def load(self, distribution, path, interpretor, trust=-99):
        for factory in self.loaders:
            loader = factory(distribution, path, interpretor, trust=trust)
            if loader is not None:
                assert loader.load() is distribution
                return loader
        raise PackageError(u"Unknow package type at", path)
