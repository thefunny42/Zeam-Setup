
from monteur.sources import Installers, Source, STRATEGY_QUICK
from monteur.sources.utils import (
    ExtractedPackageInstaller,
    PackageInstaller)
from monteur.error import PackageNotFound
from monteur.utils import create_directory
from monteur.vcs import VCS, VCSPackage
from monteur.version import Version, keyify


class VCSSource(Source):
    """This sources fetch packages from from various popular version
    control systems.
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
                yield VCSPackage(
                    package, info, info.as_words(), base=self.directory)

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

    def initialize(self, priority):
        __status__ = u"Preparing remote development sources."
        super(VCSSource, self).initialize(priority)
        if priority is None:
            return
        sources = list(self._sources())
        if sources:
            VCS.initialize()
            create_directory(self.directory)
            for source in sources:
                self.sources[keyify(source.name)] = VCS(source)

    def search(self, requirement, interpretor, strategy):
        if requirement.key in self.sources:
            source = self.sources[requirement.key]
            if self.enabled and source.name not in self.enabled:
                raise PackageNotFound(requirement)
            source = source(update=(strategy!= STRATEGY_QUICK))
            installer = self.factory(
                self, name=source.name, path=source.directory,
                version=Version.parse('latest'), trust=0)
            packages = Installers([installer]).get_installers_for(requirement)
            if packages:
                return packages
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<VCSSource at %s>' % (self.directory)
