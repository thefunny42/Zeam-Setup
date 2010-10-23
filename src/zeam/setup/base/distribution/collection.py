
import bisect

from zeam.setup.base.error import InstallationError
from zeam.setup.base.version import Requirement


class ReleaseProxy(object):
    """Proxy a release object to attach data on it.
    """

    def __init__(self, release, **items):
        self.__release = release
        self.__items = items

    def items(self):
        return self.__items

    def __getattr__(self, key):
        return getattr(self.__release, key)


class ReleaseGroup(object):
    """A release group group releases for the same software (name)
    """

    def __init__(self, name, releases=None):
        self.name = name
        if releases is None:
           releases = []
        self.releases = releases
        assert isinstance(self.releases, list), u"Releases must be a list"
        self.releases.sort()

    def add(self, release):
        if release.name != self.name:
            raise InstallationError(u'Invalid release added to collection')
        bisect.insort(self.releases, release)

    def get_most_recent(self):
        """Return the most recent release.
        """
        # Since self.releases is sorted it should be the last one
        return self.releases and self.releases[-1] or None

    def get_releases_for(self, requirement, pyversion=None, platform=None):
        """Filter out releases that doesn't match the criterias.
        """

        def releases_filter(release):
            if release.pyversion is not None:
                if pyversion != release.pyversion:
                    return False
            if release.platform is not None:
                if platform != release.platform:
                    return False
            return requirement.match(release)

        return self.__class__(
            self.name, filter(releases_filter, self.releases))

    def __getitem__(self, requirement):
        if not isinstance(requirement, Requirement):
            raise KeyError(requirement)
        return self.get_releases_for(requirement)

    def __len__(self):
        return len(self.releases)

    def __repr__(self):
        return '<Software %s>' % self.name


class ReleaseSet(object):
    """Represent the available software.
    """

    def __init__(self):
        self.releases = {}

    def add(self, release):
        """Add a software to the available ones.
        """
        set = self.releases.setdefault(release.name, ReleaseGroup(release.name))
        set.add(release)

    def extend(self, releases):
        """Extend the available software by adding a list of releases to it.
        """
        for release in releases:
            self.add(release)

    def __getitem__(self, key):
        if isinstance(key, Requirement):
            return self.releases[key.name][key]
        return self.release[key]

    def get_releases_for(self, requirement, pyversion=None, platform=None):
        if not requirement.name in self.releases:
            return []
        return self.releases[requirement.name].get_releases_for(
            requirement, pyversion=pyversion, platform=platform)
