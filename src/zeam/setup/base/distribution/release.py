
import logging
import sys

from zeam.setup.base.error import PackageError, InstallationError
from zeam.setup.base.version import Version

logger = logging.getLogger('zeam.setup')


class Release(object):
    """Represent a release of a software.
    """

    def __init__(self, name=None, version=None, path=None,
                 pyversion=None, platform=None, url=None, format=None):
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
        self.package_path = path
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


