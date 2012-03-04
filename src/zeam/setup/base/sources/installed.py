
import sys

from zeam.setup.base.distribution.workingset import working_set
from zeam.setup.base.sources import Installers, Source
from zeam.setup.base.error import PackageNotFound

marker = object()


class NullInstaller(object):
    """Don't install anything, return an already installed package.
    """

    def __init__(self, distribution):
        self.distribution = distribution

    def filter(self, requirement, pyversion=None, platform=None):
        # XXX check pyversion and blabla
        return requirement.match(self.distribution)

    def __lt__(self, other):
        return False            # This is the most recent we got.

    def __getattr__(self, key):
        value = getattr(self.distribution, key, marker)
        if value is marker:
            raise AttributeError(key)
        return value

    def install(self, path, interpretor, install_dependencies):
        install_dependencies(self.distribution)
        return self.distribution, self


class InstalledSource(Source):
    """This source report already installed packages in the Python
    path. It only works if the target interpretor is the same used to
    run the setup.
    """

    def __init__(self, *args):
        super(InstalledSource, self).__init__(*args)
        self.working_set = None
        self.packages = self.options.get('packages', '').as_list()

    def initialize(self, first_time):
        if self.working_set is None:
            self.working_set = working_set

    def available(self, configuration):
        return len(self.packages) != 0

    def search(self, requirement, interpretor):
        if interpretor == sys.executable:
            if not self.packages or requirement.name in self.packages:
                if requirement.name in self.working_set:
                    installer = NullInstaller(self.working_set[requirement])
                    packages = Installers(
                        [installer]).get_installers_for(requirement)
                    if packages:
                        return packages
        raise PackageNotFound(requirement)
