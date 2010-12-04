
import os

from zeam.setup.base.vcs.error import VCSConfigurationError, VCSError


class VCS(object):
    """Base API to access a project in a VCS.
    """

    def __init__(self, uri, directory, generic_options=[]):
        self.uri = uri
        self.directory = directory
        self.generic_options = generic_options

    def install(self):
        if not os.path.isdir(self.directory):
            if os.path.exists(self.directory):
                raise VCSError(
                    u"Checkout directory %s exists but is not a directory" % (
                        self.directory))
            self.checkout()
        else:
            # XXX Should do this only in newest mode ?
            self.update()

    def checkout(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()


class VCSFactory(object):
    """Create a new instance of a VCS worker.
    """

    def available(self):
        raise NotImplementedError()

    def __call__(self, uri, directory):
        raise NotImplementedError()


class Develop(VCS):
    """VCS VCS: no VCS, just do a symlink to the sources.
    """

    def install(self):
        if not os.path.exists(self.directory):
            os.symlink(os.path.abspath(self.uri), self.directory)


class DevelopFactory(VCSFactory):

    def available(self):
        return True

    def __call__(self, uri, directory):
        return Develop(uri, directory)


class VCSRegistry(object):
    """Register all available VCS.
    """

    def __init__(self, factories):
        self.__initialized = False
        self.__factories = factories
        self.__vcs = {}

    def initialize(self):
        """Instentiate VCS factories. This will detect if they are
        available or not.
        """
        __status__ = u"Detecting VCS systems."
        if self.__initialized:
            return
        for name, factory in self.__factories.iteritems():
            self.__vcs[name] = factory()
        self.__initialized = True

    def get(self, name, package_name, source_info):
        """Return a VCS instance called name of the package
        package_name located at source_info url.
        """
        if name not in self.__vcs:
            raise VCSConfigurationError(
                source_info.location,
                u"Unknown VCS system '%s' for package %s" % (
                    name, package_name))
        factory = self.__vcs[name]
        if not factory.available():
            raise VCSConfigurationError(
                source_info.location,
                u"VCS system '%s' is not available, "
                u"please install '%s' first" % (
                    name, factory.package_name))
        return factory
