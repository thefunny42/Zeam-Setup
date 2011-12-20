
import os

from zeam.setup.base.vcs.error import VCSConfigurationError, VCSError
from zeam.setup.base.error import ConfigurationError


class VCSCheckout(object):

    def __init__(self, name, origin, options, directory):
        self.name = name
        self.defined_at = origin.location
        if len(options) < 2:
            raise ConfigurationError(
                self.defined_at,
                u"Malformed source description for package",
                name)
        self.vcs = options[0]
        self.uri = options[1]
        self.branch = None
        self.directory = os.path.join(directory, name)

        for extra in options[2:]:
            if not '=' in extra:
                raise ConfigurationError(
                    self.defined_at,
                    u"Malformed source option for package",
                    name)
            name, value = extra.split('=', 1)
            if name in self.__dict__:
                self.__dict__[name] = value


class VCS(object):
    """Base API to access a project in a VCS.
    """

    def __init__(self, package, options=[]):
        self.package = package
        self.options = options
        self.install = None     # Method called to do the work

    @property
    def directory(self):
        return self.package.directory

    def prepare(self):
        """Determine what must be done.
        """
        if self.install is None:
            if not os.path.isdir(self.package.directory):
                if os.path.exists(self.package.directory):
                    raise VCSError(
                        u"Checkout directory exists but is not a directory",
                        self.package.directory)
                self.install = self.checkout
            else:
                # XXX Should do this only in newest mode ?
                if self.verify():
                    self.install = self.update
                else:
                    if not self.status():
                        raise VCSError(
                            u"Checkout directory must switched "
                            u"and is locally modified",
                            self.package.directory)
                    self.install = self.switch

    def __call__(self):
        self.prepare()
        assert self.install is not None
        self.install()
        return self

    def status(self):
        """Return True if the checkout is clean and have been modified.
        """
        return True

    def verify(self):
        """Return True if the checkout match the given package uri.
        """
        return True

    def checkout(self):
        """Checkout the code on the filesystem.
        """
        raise NotImplementedError()

    def update(self):
        """Update the code on the filesystem.
        """
        raise NotImplementedError()

    def switch(self):
        """Switch a branch on the filesystem.
        """
        raise NotImplementedError()


class VCSFactory(object):
    """Create a new instance of a VCS worker.
    """
    software_name = 'Unix'
    available = False
    version = '0.0'

    def __call__(self, package):
        raise NotImplementedError()


class Develop(VCS):
    """VCS VCS: no VCS, just do a symlink to the sources.
    """

    def checkout(self):
        if not os.path.exists(self.package.directory):
            os.symlink(
                os.path.abspath(self.package.uri),
                self.package.directory)

    update = checkout


class DevelopFactory(VCSFactory):
    available = True

    def __call__(self, package):
        return Develop(package)


class VCSRegistry(object):
    """Register all available VCS.
    """

    def __init__(self, factories):
        self._initialized = False
        self._factories = factories
        self._vcs = {}

    def initialize(self):
        """Instentiate VCS factories. This will detect if they are
        available or not.
        """
        __status__ = u"Detecting VCS systems."
        if self._initialized:
            return
        for name, factory in self._factories.iteritems():
            self._vcs[name] = factory()
        self._initialized = True

    def __call__(self, package):
        """Return a VCS instance called name of the package
        package_name located at source_info url.
        """
        if package.vcs not in self._vcs:
            raise VCSConfigurationError(
                package.defined_at, u"Unknown VCS system for package",
                package.vcs, package.name)
        factory = self._vcs[package.vcs]
        if not factory.available:
            raise VCSConfigurationError(
                package.defined_at,
                u"VCS system '%s' is not available, "
                u"please install '%s' first" % (
                    package.vcs, factory.software_name))
        return factory(package)
