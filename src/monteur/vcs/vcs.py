
import os

from monteur.distribution.workingset import working_set
from monteur.vcs.error import VCSConfigurationError, VCSError
from monteur.error import ConfigurationError


class VCSCheckout(object):
    """Represent a checkout or clone from a VCS repository.
    """

    def __init__(self, name, origin, options, base=None, directory=None):
        self.name = name
        defined_at = origin.location
        if len(options) < 2:
            raise ConfigurationError(
                defined_at,
                u"Malformed source description for checkout",
                name)
        self.vcs = options[0]
        self.uri = options[1]
        self.branch = None
        self.directory = None
        if base:
            assert directory is None, u"Cannot specify base and directory"
            self.directory = os.path.join(base, name)
        elif directory:
            self.directory = directory

        for extra in options[2:]:
            if not '=' in extra:
                raise ConfigurationError(
                    defined_at,
                    u"Malformed source option for checkout",
                    name)
            name, value = extra.split('=', 1)
            if name in self.__dict__:
                self.__dict__[name] = value

        # Those are not overridable options
        self.defined_at = defined_at
        self.defined_directory = origin.get_cfg_directory()


class VCS(object):
    """Base API to access a project in a VCS.
    """

    def __init__(self, checkout, options=[]):
        assert checkout.directory is not None, \
            u"Checkout not properly configured"
        self.checkout = checkout
        self.options = options
        self.install = None     # Method called to do the work

    @property
    def name(self):
        return self.checkout.name

    @property
    def directory(self):
        return self.checkout.directory

    def inspect(self, checkout=True, update=True):
        """Determine what must be done (checkout, update, switch).
        """
        if self.install is None:
            if not os.path.isdir(self.checkout.directory):
                if os.path.exists(self.checkout.directory):
                    raise VCSError(
                        u"Checkout directory exists but is not a directory",
                        self.checkout.directory)
                if checkout:
                    self.install = self.fetch
            else:
                if self.verify():
                    if update:
                        self.install = self.update
                else:
                    if not self.status():
                        raise VCSError(
                            u"Checkout directory must switched "
                            u"and is locally modified",
                            self.checkout.directory)
                    self.install = self.switch
        return self.install is not None

    def __call__(self, checkout=True, update=True):
        if self.inspect(checkout=checkout, update=update):
            self.install()
        return self

    def status(self):
        """Return True if the checkout is clean and have been modified.
        """
        return True

    def verify(self):
        """Return True if the checkout match the given checkout uri,
        False if it needs to be switched.
        """
        return True

    def fetch(self):
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

    def __call__(self, checkout):
        raise NotImplementedError()


class VCSRegistry(object):
    """Register all available VCS.
    """

    def __init__(self):
        self._initialized = False
        self._vcs = {}

    def initialize(self):
        """Instentiate VCS factories. This will detect if they are
        available or not.
        """
        __status__ = u"Detecting VCS systems."
        if self._initialized:
            return
        for name, factory in working_set.iter_all_entry_points('setup_vcs'):
            self._vcs[name] = factory()
        self._initialized = True

    def __call__(self, checkout):
        """Return a VCS instance called name of the checkout
        checkout_name located at source_info url.
        """
        if checkout.vcs not in self._vcs:
            raise VCSConfigurationError(
                checkout.defined_at, u"Unknown VCS system for checkout",
                checkout.vcs, checkout.name)
        factory = self._vcs[checkout.vcs]
        if not factory.available:
            raise VCSConfigurationError(
                checkout.defined_at,
                u"VCS system '%s' is not available, "
                u"please install '%s' first" % (
                    checkout.vcs, factory.software_name))
        return factory(checkout)
