
import bisect

from zeam.setup.base.error import InstallationError
from zeam.setup.base.version import Requirement


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

    def __init__(self):
        self.installers = {}

    def add(self, installer):
        """Add a software to the available ones.
        """
        default = PackageInstallers(installer.name)
        installers = self.installers.setdefault(installer.name, default)
        installers.add(installer)

    def extend(self, installers):
        """Extend the available software by adding a list of installers to it.
        """
        for installer in installers:
            self.add(installer)

    def __len__(self):
        return len(self.installers)

    def __getitem__(self, key):
        if isinstance(key, Requirement):
            return self.installers[key.name][key]
        return self.installer[key]

    def get_installers_for(self, requirement, pyversion=None, platform=None):
        if not requirement.name in self.installers:
            return []
        return self.installers[requirement.name].get_installers_for(
            requirement, pyversion=pyversion, platform=platform)
