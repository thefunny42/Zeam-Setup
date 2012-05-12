
import os

from zeam.setup.base.error import InstallationError, PackageNotFound
from zeam.setup.base.sources import Installers, Source
from zeam.setup.base.distribution.workingset import working_set

from zeam.setup.base.sources.utils import ExtractedPackageInstaller


class ExtensionsSource(Source):
    """This source advertise packages that is included within already
    existing packages, as extensions. Those packages are made
    available through the help of entry points.
    """

    def __init__(self, *args):
        __status__ = u"Initializing extensions sources."
        super(ExtensionsSource, self).__init__(*args)
        self.sources = {}
        self.availables = None
        if 'available' in self.options:
            self.availables = self.options['available'].as_list()

    def initialize(self, priority):
        __status__ = u"Preparing extensions sources."
        super(ExtensionsSource, self).initialize(priority)
        if priority is None:
            return
        for package_name, package in working_set.iter_all_entry_points(
            'setup_extensions'):
            if self.availables is not None and package_name not in self.availables:
                continue
            if not hasattr(package, '__path__'):
                raise InstallationError(
                    u"Invalid extension entry point", package_name)
            directory = package.__path__[0]
            for name in os.listdir(directory):
                full_directory = os.path.join(directory, name)
                if os.path.isdir(full_directory):
                    if name in self.sources:
                        raise InstallationError(
                            u'Duplicate extension source',
                            full_directory,
                            self.sources[name])
                    self.sources[name] = full_directory

    def search(self, requirement, interpretor, strategy):
        name = requirement.name
        if name in self.sources:
            installer = ExtractedPackageInstaller(
                self, name=name, path=self.sources[name], trust=0)
            packages = Installers([installer]).get_installers_for(requirement)
            if packages:
                return packages
        raise PackageNotFound(requirement)

