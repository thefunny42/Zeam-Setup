
import bisect
import logging
import os
import sys

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.error import PackageError, InstallationError
from zeam.setup.base.version import Version, Requirement, Requirements

logger = logging.getLogger('zeam.setup')


class Software(object):
    """A software is composed by a list of release of the same
    software.
    """

    def __init__(self, name, releases=None):
        self.name = name
        self.releases = releases
        if self.releases is None:
            self.releases = []
        assert isinstance(self.releases, list), u"Releases must be a list"
        self.releases.sort()

    def add(self, release):
        if release.name != self.name:
            raise InstallationError(u'Invalid release added to collection')
        bisect.insort(self.releases, release)

    def __getitem__(self, requirement):
        if not isinstance(requirement, Requirement):
            raise KeyError(requirement)
        return self.__class__(
            self.name, filter(requirement.match, self.releases))

    def __len__(self):
        return len(self.releases)

    def __repr__(self):
        return '<Software %s>' % self.name


class Release(object):
    """Represent a release of a software.
    """

    def __init__(self, name, version, format='tar.gz', url='http://google.com',
                 pyversion=None, platform=None):
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
        self.path = None
        self.entry_points = {}
        self.requirements = []
        self.extras = {}

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

    def __repr__(self):
        return '<%s for %s version %s>' % (
            self.__class__.__name__, self.name, self.version)


class UninstalledRelease(Release):
    """A release that you can download.
    """
    pass




class DevelopmentRelease(Release):
    """A development release located on the file system.
    """

    def __init__(self, path=None, config=None):
        if config is None:
            if path is not None:
                config = self.__load_egg_config(path)
            else:
                raise PackageError(
                    u'Need a path or a config to create a development release')
        elif path is None:
            path = config.get_cfg_directory()
        self.__load_egg_info(config, path)

    def __load_egg_config(self, path):
        path = os.path.abspath(path)
        setup_cfg_path = os.path.join(path, 'setup.cfg')
        if not os.path.isfile(setup_cfg_path):
            raise PackageError(path, 'No setup.cfg information')
        return Configuration.read(setup_cfg_path)

    def __load_egg_info(self, config, path):
        egginfo = config['egginfo']

        self.name = egginfo['name'].as_text()
        self.version = Version.parse(egginfo['version'].as_text())
        self.summary = egginfo.get('summary', '').as_text()
        self.author = egginfo.get('author', '').as_text()
        self.author_email = egginfo.get('author_email', '').as_text()
        self.license = egginfo.get('license', '').as_text()
        self.classifiers = egginfo.get('classifier', '').as_list()
        self.format = None
        self.url = path
        self.pyversion = None
        self.platform = None
        self.requirements = Requirements.parse(
            egginfo.get('requires', '').as_list())
        self.extras = {}

        # Source path of the extension
        source_path = os.path.join(path, egginfo.get('source', '.').as_text())
        if not os.path.isdir(source_path):
            raise PackageError(path, 'Invalid source path "%s"' % source_path)
        self.path = os.path.abspath(source_path)

        # Entry points
        self.entry_points = {}
        entry_points = egginfo.get('entry_points', None)
        if entry_points is not None:
            for category_name in entry_points.as_list():
                info = config['entry_points:' + category_name]
                self.entry_points[category_name] = info.as_dict()


