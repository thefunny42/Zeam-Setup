
from zeam.setup.base.sources import Installers, Source
from zeam.setup.base.sources.utils import (
    ExtractedPackageInstaller,
    PackageInstaller)
from zeam.setup.base.error import PackageNotFound
from zeam.setup.base.utils import create_directory
from zeam.setup.base.vcs import VCS, VCSCheckout



class VCSSource(Source):
    """This sources fetch the code from various popular version
    control system.
    """

    def __init__(self, *args):
        __status__ = u"Initializing remote development sources."
        super(VCSSource, self).__init__(*args)
        self.directory = self.options['directory'].as_text()
        self.sources = {}
        self.enabled = None
        self.develop = self.options.get('develop', 'on').as_bool()
        if 'available' in self.options:
            self.enabled = self.options['available'].as_list()
        self.factory = ExtractedPackageInstaller
        if self.develop:
            self.factory = PackageInstaller

    def _sources(self):
        configuration = self.options.configuration
        for name in self.options['sources'].as_list():
            section = configuration['vcs:' + name]
            for package, info in section.items():
                yield VCSCheckout(
                    package, info, info.as_words(), self.directory)

    def is_uptodate(self):
        __status__ = u"Verifying changes in development sources."
        uptodate = super(VCSSource, self).is_uptodate()
        if uptodate and self.installed_options is not None:
            configuration = self.options.configuration
            installed_configuration = self.installed_options.configuration
            for name in self.options['sources'].as_list():
                key = 'vcs:' + name
                if configuration[key] != installed_configuration.get(key, None):
                    return False
        return True

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
