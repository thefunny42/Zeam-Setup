
import os

from monteur.sources import Installers, Source, Query
from monteur.sources.utils import (
    parse_filename,
    UninstalledPackageInstaller,
    PackageInstaller)
from monteur.utils import create_directory


class LocalSource(Source):
    """This represent a directory with a list of archives, that can be
    used to install software.
    """
    installer_factory = UninstalledPackageInstaller
    type = 'Archive Source'
    directory = 'download_directory'
    TRUST = -99

    def __init__(self, *args):
        __status__ = u"Initializing local software source."
        super(LocalSource, self).__init__(*args)
        self.paths = self.options[self.directory].as_list()

    def get_information(self, path):
        """Get a list of installer from a directory.
        """
        for filename in os.listdir(path):
            full_path = os.path.join(path, filename)
            if not os.path.isfile(full_path):
                continue
            information = parse_filename(filename, url=full_path)
            if information:
                yield information

    def prepare(self, context):
        __status__ = u"Analysing local software source %s." % (
            ', '.join(self.paths))
        installers = Installers()

        def build_installer(informations):
            return self.installer_factory(context, **informations)

        for path in self.paths:
            create_directory(path)
            installers.extend(map(build_installer, self.get_information(path)))
        if installers:
            return Query(context, installers)
        return None

    def __repr__(self):
        return '<%s at %s>' % (self.type, ', '.join(self.paths))


class EggsSource(LocalSource):
    """This manage installed sources.
    """
    installer_factory = PackageInstaller
    type = 'Eggs'
    directory = 'lib_directory'

    def get_information(self, path):
        """Get a list of egg installers from a directory
        """
        for filename in os.listdir(path):
            full_path = os.path.join(path, filename)
            if not os.path.isdir(full_path):
                continue
            information = parse_filename(filename, path=full_path)
            if information:
                yield information
