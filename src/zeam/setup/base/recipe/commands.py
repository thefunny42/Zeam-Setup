
import logging

from zeam.setup.base.distribution.workingset import WorkingSet
from zeam.setup.base.configuration import Section
from zeam.setup.base.error import ConfigurationError, PackageNotFound
from zeam.setup.base.installer import PackageInstaller
from zeam.setup.base.version import Requirements

logger = logging.getLogger('zeam.setup')


class PartInstalled(object):

    def __init__(self, name):
        self.__name = 'installed:' + name
        self.__paths = []
        self.__packages = WorkingSet()

    def add_path(self, pathname):
        self.__paths.append(pathname)

    def add_paths(self, pathnames):
        self.__paths.extend(pathnames)

    def add_packages(self, working_set):
        for package in working_set.installed.values():
            self.__packages.add(package)

    def save(self, configuration):
        section = Section(self.__name, configuration=configuration)
        if self.__paths:
            section['paths'] = self.__paths
        if self.__packages:
            section['packages'] = self.__packages.as_requirements()
        configuration[self.__name] = section
        return section


class Part(object):

    def __init__(self, name, section, install_set):
        self.name = name
        self.recipes = []
        self.installed = PartInstalled(name)
        # For installation only
        installer = PackageInstaller(section, install_set)
        get_entry_point = install_set.get_entry_point

        def install_packages(names):
            installer(Requirements.parse(names))
            for name in names:
                install_set.get(name).activate()

        for recipe in section['recipe'].as_list():
            try:
                factory = get_entry_point('setup_installers', recipe)
            except PackageNotFound, error:
                # The package is not installed, install it and try again
                install_packages([error.args[0]])
                factory = get_entry_point('setup_installers', recipe)

            if factory is None:
                raise ConfigurationError(u"Could load recipe", recipe)
            instance = factory(section)
            # Install dynamic dependencies if required
            install_packages(instance.requirements)
            self.recipes.append(instance)

    def prepare(self):
        for recipe in self.recipes:
            recipe.prepare(self.installed)

    def install(self):
        for recipe in self.recipes:
            recipe.install(self.installed)

    def finalize(self, configuration):
        self.installed.save(configuration)


class Installer(object):
    """Install an environment.
    """

    def __init__(self, configuration):
        __status__ = u"Loading installation recipes."
        self.configuration = configuration

        # Setup working set: used only for installation
        install_set = WorkingSet()
        # Lookup parts
        self.parts = []
        setup = configuration['setup']
        for name in setup['install'].as_list():
            self.parts.append(Part(name, self.configuration[name], install_set))

    def run(self):
        __status__ = u"Preparing installation."
        # Organise recipe order
        # Look for update/uninstall/install

        # Prepare recipe
        for part in self.parts:
            part.prepare()

        # Uninstall in reverse order of install
        # Update
        # Install in order
        __status__ = u"Running installation."
        for part in self.parts:
            part.install()

        # Save status
        __status__ = u"Finalize installation."
        for part in self.parts:
            part.finalize(self.configuration)

