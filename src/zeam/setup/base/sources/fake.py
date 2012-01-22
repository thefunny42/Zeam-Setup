
import operator
import os

from zeam.setup.base.distribution.release import Release
from zeam.setup.base.egginfo.write import write_egg_info
from zeam.setup.base.error import PackageNotFound
from zeam.setup.base.sources import Installers
from zeam.setup.base.version import Version, Requirements


class FakeInstaller(object):
    """Doesn't install anything, fake a distribution for a requirement.
    """

    def __init__(self, requirement, trust=10):
        self.name = requirement.name
        self.key = requirement.key
        self.trust = trust      # Level of quality of the packaging.
        if (len(requirement.versions) == 1 and
            requirement.versions[0][0] == operator.eq):
            self.version = requirement.versions[0][1]
        else:
            self.version = Version.parse('0.0')
        self.extras = {}
        for extra in requirement.extras:
            self.extras[extra] = Requirements()

    def __lt__(self, other):
        return True

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


class FakeSource(object):
    """This source fake packages without installing them.
    """

    def __init__(self, options):
        __status__ = u"Initializing fake source."
        self.options = options
        self.installers = Installers()
        for requirement in Requirements.parse(
            options.get('packages', '').as_list()):
            self.installers.add(FakeInstaller(requirement))

    def initialize(self, first_time):
        pass

    def available(self, configuration):
        # This source provider is available if there are packages
        return bool(len(self.installers))

    def search(self, requirement, interpretor):
        packages = self.installers.get_installers_for(requirement)
        if packages:
            return packages
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<FakeSource>'
