
import shutil
import tempfile
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
        self.__paths = set([])
        self.__packages = WorkingSet()

    def add_path(self, pathname):
        if pathname:
            self.__paths.add(pathname)

    def update_path(self, old_path, new_path):
        if old_path:
            self.__paths.remove(old_path)
        if new_path:
            self.__paths.add(new_path)

    def add_paths(self, pathnames):
        if pathnames:
            self.__paths.update(pathnames)

    @property
    def paths(self):
        return list(self.__paths)

    def add_packages(self, working_set):
        for package in working_set.installed.values():
            self.__packages.add(package)

    def save(self, configuration):
        section = Section(self.__name, configuration=configuration)
        if self.__paths:
            section['paths'] = list(self.__paths)
        if self.__packages:
            section['packages'] = self.__packages.as_requirements()
        configuration[self.__name] = section
        return section


class Part(object):

    def __init__(self, name, section, install_set, install_set_directory):
        logger.info('Load installation for %s' % name)
        self.name = name
        self.recipes = []
        self.installed = PartInstalled(name)
        # For installation only
        installer = PackageInstaller(section, install_set)
        get_entry_point = install_set.get_entry_point

        def install_packages(names):
            installer(
                Requirements.parse(names), directory=install_set_directory)
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
        logger.warn('Prepare installation for %s.' % self.name)
        for recipe in self.recipes:
            recipe.prepare(self.installed)

    def install(self):
        logger.warn('Install %s.' % self.name)
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
        self.install_deps_directory = tempfile.mkdtemp('zeam.setup.install')

        # Lookup parts
        self.parts = []
        setup = configuration['setup']
        for name in setup['install'].as_list():
            part = Part(
                name,
                self.configuration[name],
                install_set,
                self.install_deps_directory)
            self.parts.append(part)

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

        # Remove unused software.
        shutil.rmtree(self.install_deps_directory)
