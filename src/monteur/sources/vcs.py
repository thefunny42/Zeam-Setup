
from monteur.sources import Installers, Source, Context, STRATEGY_QUICK
from monteur.utils import create_directory
from monteur.vcs import VCS, VCSCheckout
from monteur.version import keyify
from monteur.distribution.release import Release

marker = object()


class SourceInstaller(object):

    def __init__(self, context, **informations):
        self.context = context
        self.release = Release(**informations)
        # We need to load the release now to have the proper version
        self.loader = context.load(self.release)

    def filter(self, requirement, pyversion=None, platform=None):
        return requirement.match(self.release)

    def __lt__(self, other):
        return ((self.version, -self.context.priority) <
                (other.version, -other.context.priority))

    def __getattr__(self, key):
        value = getattr(self.release, key, marker)
        if value is marker:
            raise AttributeError(key)
        return value

    def install(self, path, install_dependencies):
        install_dependencies(self.release)
        if self.context.develop:
            # Build files
            self.loader.build(path)
        else:
            # Install files
            install_path = self.context.get_install_path(path, self.release)
            self.loader.install(path)

            # Package path is now the installed path
            self.release.path = install_path
            self.release.package_path = install_path

        return self.release, self.loader


class VCSQuery(object):

    def __init__(self, context, sources):
        self.context = context
        self.sources = sources

    def __call__(self, requirement, strategy):
        if requirement.key in self.sources:
            source = self.sources[requirement.key]
            checkout = source(update=(strategy!= STRATEGY_QUICK))
            installer = SourceInstaller(
                self.context, name=source.name, path=checkout.directory)
            return Installers([installer]).get_installers_for(requirement)
        return []


class VCSContext(Context):

    def __init__(self, source, interpretor, priority, trust=0):
        super(VCSContext, self).__init__(source, interpretor, priority, trust)
        self.develop = source.develop


class VCSSource(Source):
    """This sources fetch packages from from various popular version
    control systems.
    """
    Context = VCSContext

    def __init__(self, *args):
        __status__ = u"Initializing remote development sources."
        super(VCSSource, self).__init__(*args)
        self.directory = self.options['directory'].as_text()
        self.enabled = None
        self.develop = self.options.get('develop', 'on').as_bool()
        if 'available' in self.options:
            self.enabled = self.options['available'].as_list()

    def get_checkouts(self):
        configuration = self.options.configuration
        for name in self.options['sources'].as_list():
            section = configuration['vcs:' + name]
            for package, info in section.items():
                yield VCSCheckout(
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

    def prepare(self, context):
        __status__ = u"Preparing remote development sources."
        checkouts = list(self.get_checkouts())
        if checkouts:
            VCS.initialize()
            create_directory(self.directory)
            sources = {}
            for checkout in checkouts:
                if self.enabled and checkout.name not in self.enabled:
                    continue
                sources[keyify(checkout.name)] = VCS(checkout)
            return VCSQuery(context, sources)
        return None

    def __repr__(self):
        return '<VCSSource at %s>' % (self.directory)
