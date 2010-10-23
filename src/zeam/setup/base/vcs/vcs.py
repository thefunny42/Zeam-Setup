
import os

from zeam.setup.base.vcs.error import VCSConfigurationError, VCSError


class VCSFactory(object):
    """Create a new instance of a VCS worker.
    """

    def available(self):
        raise NotImplementedError()

    def __call__(self, uri, directory):
        raise NotImplementedError()


class VCS(object):
    """Base API to access a project in a VCS.
    """

    def __init__(self, uri, directory):
        self.uri = uri
        self.directory = directory

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


class VCSRegistry(object):

    def __init__(self, vcs):
        self.__vcs = vcs

    def get(self, name, package_name, source_info):
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
