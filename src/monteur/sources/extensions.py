
import os

from monteur.distribution.workingset import working_set
from monteur.error import InstallationError
from monteur.sources import Installers, Source, Query
from monteur.sources.utils import ExtractedPackageInstaller


class ExtensionsSource(Source):
    """This source advertise packages that is included within already
    existing packages, as extensions. Those packages are made
    available through the help of entry points.
    """

    def __init__(self, *args):
        __status__ = u"Initializing extensions sources."
        super(ExtensionsSource, self).__init__(*args)
        self.enabled = None
        if 'available' in self.options:
            self.enabled = self.options['available'].as_list()

    def prepare(self, context):
        __status__ = u"Preparing extensions sources."
        installers = Installers()
        for name, package in working_set.iter_all_entry_points(
            'setup_extensions'):
            if self.enabled is not None and name not in self.enabled:
                continue
            if not hasattr(package, '__path__'):
                raise InstallationError(u"Invalid extension entry point", name)
            directory = package.__path__[0]
            for name in os.listdir(directory):
                path = os.path.join(directory, name)
                if os.path.isdir(path):
                    if name in installers:
                        raise InstallationError(
                            u'Duplicate extension source',
                            path,
                            installers[name])
                    installers.add(ExtractedPackageInstaller(
                            context, name=name, path=path))
        if installers:
            return Query(context, installers)
        return None
