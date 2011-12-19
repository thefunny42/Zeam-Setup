
import shlex

from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.vcs import VCSCheckout, VCS
from zeam.setup.base.error import ConfigurationError
from zeam.setup.base.utils import create_directory


class VersionSystemCheckout(Recipe):

    def __init__(self, options, status):
        __status__ = u"Reading VCS URIs."
        super(VersionSystemCheckout, self).__init__(options, status)
        self.directory = options['directory'].as_text()
        self.uris = []
        self.repositories = []

        uris = options['uris']
        for index, line in enumerate(uris.as_list()):
            try:
                values = shlex.split(line)
            except ValueError:
                raise ConfigurationError(
                    uris.location,
                    u"Malformed URIs for option %s on line %d" % (
                        uris.name, index))
            self.uris.append(
                VCSCheckout(values[0], uris, values[1:], self.directory))

    def prepare(self):
        __status__ = u"Preparing VCS URIs."
        if self.uris:
            VCS.initialize()
            create_directory(self.directory)
            for uri in self.uris:
                repository = VCS(uri)
                repository.prepare()
                self.repositories.append(repository)

    def install(self):
        __status__ = u"Checkout VCS URIs."
        for repository in self.repositories:
            repository.install()
            self.status.paths.add(repository.directory)
