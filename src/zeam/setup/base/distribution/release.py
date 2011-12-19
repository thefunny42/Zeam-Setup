
import logging
import sys
from distutils.util import get_platform

from zeam.setup.base.egginfo.loader import EggLoaderFactory
from zeam.setup.base.setuptools.interpreted_loader import \
    InterpretedSetuptoolsLoaderFactory
from zeam.setup.base.setuptools.native_loader import \
    NativeSetuptoolsLoaderFactory
from zeam.setup.base.distribution.loader import SetupLoaderFactory, SetupLoader
from zeam.setup.base.error import PackageError, InstallationError
from zeam.setup.base.version import Version

logger = logging.getLogger('zeam.setup')


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
        # XXX Should check dependencies here as well
        sys.path.insert(len(sys.path) and 1 or 0, self.path)

    def get_egg_directory(self, interpretor):
        """Return a directory name suitable to store the egg,
        compatible with setuptools format.
        """
        interpretor_pyversion = interpretor.get_pyversion()
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
        (python_path, attribute) = self.entry_points[group][name].split(':')
        try:
            python_module = __import__(
                python_path, globals(), globals(), [attribute])
        except ImportError:
            raise PackageError(
                self.name,
                u'Invalid module %s for entry point %s %s:%s' % (
                    python_path, group, self.name, name))
        try:
            entry_point = getattr(python_module, attribute)
        except AttributeError:
            raise PackageError(
                self.name,
                u'Invalid attribute %s in module %s ' \
                    'for entry point %s %s:%s' % (
                    attribute, python_path, group, self.name, name))
        return entry_point

    def __str__(self):
        return '%s == %s' % (self.name, self.version)

    def __repr__(self):
        return '<%s for %s version %s>' % (
            self.__class__.__name__, self.name, self.version)


POSSIBLE_LOADERS = {
    'egg': EggLoaderFactory(),
    'interpreted_setuptools': InterpretedSetuptoolsLoaderFactory(),
    'native_setuptools': NativeSetuptoolsLoaderFactory(),
    'zeam_setup': SetupLoaderFactory(),
    }
LOADERS = []


def set_loaders(names):
    global LOADERS
    LOADERS = []
    for name in names:
        if name in POSSIBLE_LOADERS:
            LOADERS.append(POSSIBLE_LOADERS[name])

set_loaders(['egg', 'native_setuptools', 'zeam_setup'])


def load_metadata(distribution, path, interpretor):
    for factory in LOADERS:
        loader = factory(distribution, path, interpretor)
        if loader is not None:
            assert loader.load() is distribution
            return loader
    else:
        raise PackageError(u"Unknow package type at %s" % (path))


def load_package(path, interpretor):
    release = Release()
    try:
        load_metadata(release, path, interpretor)
    except PackageError:
        return None
    return release


def current_package(configuration):
    loader = SetupLoader(configuration, Release())
    return loader.load()


