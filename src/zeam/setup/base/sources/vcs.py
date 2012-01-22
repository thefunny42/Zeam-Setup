
from zeam.setup.base.sources import Installers
from zeam.setup.base.sources.utils import (
    ExtractedPackageInstaller,
    PackageInstaller)
from zeam.setup.base.error import PackageNotFound
from zeam.setup.base.utils import create_directory
from zeam.setup.base.vcs import VCS, VCSCheckout



class VCSSource(object):
    """This sources fetch the code from various popular version
    control system.
    """

    def __init__(self, options):
        __status__ = u"Initializing remote development sources."
        self.options = options
        self.directory = options['directory'].as_text()
        self.sources = {}
        self.enabled = None
        self.develop = options.get('develop', 'on').as_bool()
        if 'available' in options:
            self.enabled = options['available'].as_list()
        self.factory = ExtractedPackageInstaller
        if self.develop:
            self.factory = PackageInstaller

    def _sources(self):
        for name in self.options['sources'].as_list():
            section = self.options.configuration['vcs:' + name]
            for package, info in section.items():
                yield VCSCheckout(
                    package, info, info.as_words(), self.directory)

    def initialize(self, first_time):
        __status__ = u"Preparing remote development sources."
        if not first_time:
            return
        sources = list(self._sources())
        if sources:
            VCS.initialize()
            create_directory(self.directory)
            for source in sources:
                self.sources[source.name] = VCS(source)

    def available(self, configuration):
        # This source provider is always available
        return True

    def search(self, requirement, interpretor):
        name = requirement.name
        if name in self.sources:
            if self.enabled and name not in self.enabled:
                raise PackageNotFound(requirement)
            source = self.sources[name]()
            installer = self.factory(
                self, name=name, path=source.directory, trust=0)
            packages = Installers([installer]).get_installers_for(requirement)
            if packages:
                return packages
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<VCSSource at %s>' % (self.directory)
