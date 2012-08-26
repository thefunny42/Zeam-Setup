
import shutil
import shlex

from monteur.sources import STRATEGY_QUICK
from monteur.recipe.recipe import Recipe
from monteur.vcs import VCSPackage, VCS
from monteur.vcs.error import VCSError
from monteur.error import ConfigurationError
from monteur.utils import create_directory
from monteur.recipe.utils import MultiTask


class VersionSystemCheckout(Recipe):

    def __init__(self, options, status):
        __status__ = u"Reading VCS URIs."
        super(VersionSystemCheckout, self).__init__(options, status)
        self.directory = options['directory'].as_text()
        self.packages = {}
        self.repositories = []

        uris = options['uris']
        for index, line in enumerate(uris.as_list()):
            try:
                values = shlex.split(line)
            except ValueError:
                raise ConfigurationError(
                    uris.location,
                    u"Malformed URIs for option %s on line %d." % (
                        uris.name, index))
            package = VCSPackage(
                values[0], uris, values[1:], base=self.directory)
            if package.directory in self.packages:
                raise ConfigurationError(
                    uris.location,
                    u"Duplicate checkout directory for %s on line %d." %(
                        package.name, index))
            self.packages[package.directory] = package

        self._do = MultiTask(options, 'vcs')

    def preinstall(self):
        __status__ = u"Preparing installing VCS directories."
        if self.packages:
            VCS.initialize()
            create_directory(self.directory)
            update = self.status.strategy != STRATEGY_QUICK

            def prepare(package):
                repository = VCS(package)
                repository.inspect(update=update)
                return repository

            self.repositories.extend(self._do(prepare, self.packages.values()))

    def install(self):
        __status__ = u"Checkout VCS directories."

        def install(repository):
            if repository.install is not None:
                repository.install()
            return repository.directory

        self.status.paths.extend(self._do(install, self.repositories))

    def preuninstall(self):
        __status__ = u"Prepare to remove VCS directories."
        paths = self.status.installed_paths.as_list()
        if paths:
            VCS.initialize()

            def status(path):
                if path not in self.packages:
                    raise ConfigurationError(
                        u"Missing VCS repository definition for",
                        path)
                repository = VCS(self.packages[path])
                if not repository.status():
                    raise VCSError(
                        u"Checkout directory has local modification "
                        u"and is scheduled to be deleted", path)
                return repository

            self.repositories.extend(self._do(status, paths))

    def uninstall(self):
        __status__ = u"Removing VCS directories."
        for path in self.status.installed_paths.as_list():
            shutil.rmtree(path)
