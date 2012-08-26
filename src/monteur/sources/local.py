
import os

from monteur.sources import Installers, Source
from monteur.sources.utils import (
    get_installer_from_name,
    UninstalledPackageInstaller,
    PackageInstaller)
from monteur.error import PackageNotFound
from monteur.utils import create_directory


def get_installers_from_directory(source, path):
    """Get a list of installer from a directory.
    """
    for filename in os.listdir(path):
        full_path = os.path.join(path, filename)
        if not os.path.isfile(full_path):
            continue
        installer = get_installer_from_name(source, filename, url=full_path)
        if installer is not None:
            yield installer

def get_eggs_from_directory(source, path):
    """Get a list of egg installers from a directory
    """
    for filename in os.listdir(path):
        full_path = os.path.join(path, filename)
        if not os.path.isdir(full_path):
            continue
        installer = get_installer_from_name(source, filename, path=full_path)
        if installer is not None:
            yield installer


class LocalSource(Source):
    """This represent a directory with a list of archives, that can be
    used to install software.
    """
    factory = UninstalledPackageInstaller
    type = 'Archive Source'
    directory = 'download_directory'
    finder = get_installers_from_directory

    def __init__(self, *args):
        __status__ = u"Initializing local software source."
        super(LocalSource, self).__init__(*args)
        self.paths = self.options[self.directory].as_list()
        self.installers = Installers()

    def initialize(self, priority):
        __status__ = u"Analysing local software source %s." % (
            ', '.join(self.paths))
        super(LocalSource, self).initialize(priority)
        for path in self.paths:
            if priority is not None:
                create_directory(path)
            self.installers.extend(self.finder(path))

    def search(self, requirement, interpretor, strategy):
        __status__ = u"Locating local source for %s in %s." % (
            requirement, ', '.join(self.paths))
        pyversion = interpretor.get_version()
        platform = interpretor.get_platform()
        packages = self.installers.get_installers_for(
            requirement, pyversion, platform)
        if packages:
            return packages
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<%s at %s>' % (self.type, ', '.join(self.paths))


class EggsSource(LocalSource):
    """This manage installed sources.
    """
    factory = PackageInstaller
    type = 'Eggs'
    directory = 'lib_directory'
    finder = get_eggs_from_directory
