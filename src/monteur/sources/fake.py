
import operator
import os

from monteur.distribution.release import Release
from monteur.egginfo.write import write_egg_info
from monteur.sources import Installers, Source, Query
from monteur.version import Version, Requirements


class FakeInstaller(object):
    """Doesn't install anything, fake a distribution for a requirement.
    """

    def __init__(self, context, requirement):
        self.context = context
        self.name = requirement.name
        self.key = requirement.key
        if (len(requirement.versions) == 1 and
            requirement.versions[0][0] == operator.eq):
            self.version = requirement.versions[0][1]
        else:
            self.version = Version.parse('latest')
        self.extras = {}
        for extra in requirement.extras:
            self.extras[extra] = Requirements()

    def __lt__(self, other):
        return ((self.version, -self.context.priority) <
                (other.version, -other.context.priority))

    def filter(self, requirement, pyversion=None, platform=None):
        return requirement.match(self)

    def install(self, install_dependencies):
        distribution = Release(name=self.name, version=self.version)
        distribution.extras = self.extras.copy()

        # Create a fake egg-info to make setuptools entry points works
        # if the package is a dependency.
        install_path = self.context.get_install_path(distribution)
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
        self.requirements = Requirements.parse(
            self.options.get('packages', '').as_list())

    def prepare(self, context):
        if len(self.requirements):
            installers = Installers()
            for requirement in self.requirements:
                installers.add(FakeInstaller(
                        context,
                        requirement))
            return Query(context, installers)
        return None
