
import operator
import os

from monteur.distribution.release import Release
from monteur.egginfo.write import write_egg_info
from monteur.error import PackageNotFound
from monteur.sources import Installers, Source
from monteur.version import Version, Requirements


class FakeInstaller(object):
    """Doesn't install anything, fake a distribution for a requirement.
    """

    def __init__(self, source, requirement, trust=10):
        self.source = source
        self.name = requirement.name
        self.key = requirement.key
        self.trust = trust      # Level of quality of the packaging.
        if (len(requirement.versions) == 1 and
            requirement.versions[0][0] == operator.eq):
            self.version = requirement.versions[0][1]
        else:
            self.version = Version.parse('latest')
        self.extras = {}
        for extra in requirement.extras:
            self.extras[extra] = Requirements()

    def __lt__(self, other):
        return ((self.version, -self.source.priority) <
                (other.version, -other.source.priority))

    def filter(self, requirement, pyversion=None, platform=None):
        return requirement.match(self)

    def install(self, path, interpretor, install_dependencies):
        distribution = Release(name=self.name, version=self.version)
        distribution.extras = self.extras.copy()

        # Create a fake egg-info to make setuptools entry points works
        # if the package is a dependency.
        install_path = os.path.join(
            path, distribution.get_egg_directory(interpretor))
        if not os.path.isdir(install_path):
            os.makedirs(install_path)
        write_egg_info(distribution, package_path=install_path)

        # Package path is now the installed path
        distribution.path = install_path
        distribution.package_path = install_path
        return distribution, self


class FakeSource(Source):
    """This source fake packages without installing them.
    """

    def __init__(self, *args):
        __status__ = u"Initializing fake source."
        super(FakeSource, self).__init__(*args)
        self.installers = Installers()
        for requirement in Requirements.parse(
            self.options.get('packages', '').as_list()):
            self.installers.add(FakeInstaller(self, requirement))

    def available(self, configuration):
        # This source provider is available if there are packages
        return bool(len(self.installers))

    def search(self, requirement, interpretor, strategy):
        packages = self.installers.get_installers_for(requirement)
        if packages:
            return packages
        raise PackageNotFound(requirement)
