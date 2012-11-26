

from monteur.distribution.workingset import WorkingSet
from monteur.sources import Installers, Source, Query

marker = object()


class NullInstaller(object):
    """Don't install anything, return an already installed package.
    """

    def __init__(self, context, release):
        self.context = context
        self.release = release

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
        return self.release, self


class InstalledSource(Source):
    """This source report already installed packages in the Python
    path. It only works if the target interpretor is the same used to
    run the setup.
    """

    def __init__(self, *args):
        super(InstalledSource, self).__init__(*args)
        self.enabled = None
        if 'available' in self.options:
            self.enabled = self.options.get('available', '').as_list()

    def prepare(self, context):
        if self.enabled:
            installers = Installers()
            for candidate in WorkingSet(context.interpretor, no_activate=False):
                if self.enabled is not None and candidate.name in self.enabled:
                    installers.add(NullInstaller(context, candidate))
            if installers:
                return Query(context, installers)
        return None
