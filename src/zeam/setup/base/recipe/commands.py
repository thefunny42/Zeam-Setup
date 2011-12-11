
import os
import shutil
import tempfile
import logging
import operator

from zeam.setup.base.distribution.workingset import WorkingSet
from zeam.setup.base.configuration import Section
from zeam.setup.base.error import ConfigurationError, PackageNotFound
from zeam.setup.base.installer import PackageInstaller
from zeam.setup.base.version import Requirements

logger = logging.getLogger('zeam.setup')
_marker = object()

class Paths(object):

    def __init__(self, paths=None):
        self.__data = {}
        self.__len = 0
        if paths:
            self.extend(paths)

    def add(self, path):
        data = self.__data
        for piece in path.split(os.path.sep):
            data = data.setdefault(piece, {})
        data[None] = None
        self.__len += 1

    def extend(self, paths):
        for path in paths:
            self.add(path)

    @property
    def current(self):
        return self.as_list(True)

    def as_list(self, simplify=False):
        result = []

        def build(prefix, data):
            for key, value in sorted(data.items(), key=operator.itemgetter(0)):
                if key is None:
                    result.append(os.path.sep.join(prefix))
                    if simplify:
                        # None is always the smallest.
                        break
                else:
                    build(prefix + [key], value)

        build([], self.__data)
        return result

    def __len__(self):
        return self.__len

    def __contains__(self, path):
        data = self.__data
        for piece in path.split(os.path.sep):
            data = data.get(piece, _marker)
            if data is _marker:
                return False
        if None in data:
            return True
        return False


class PartInstalled(object):

    def __init__(self, section):
        self.__name = 'installed:' + section.name
        installed_paths = []
        installed_section = section.utilities.installed.get(self.__name, None)
        if installed_section is not None:
            installed_paths = installed_section.get('paths', '').as_list()
        self.packages = WorkingSet()
        self.paths = Paths()
        self.installed_paths = Paths(installed_paths)

    def save(self, configuration):
        section = Section(self.__name, configuration=configuration)
        if self.paths:
            section['paths'] = self.paths.as_list()
        if self.packages:
            section['packages'] = self.packages.as_requirements()
        configuration[self.__name] = section
        return section


class Part(object):

    def __init__(self, section, install_set, install_set_directory):
        logger.info('Load installation for %s' % section.name)
        self.name = section.name
        self.recipes = []
        self.installed = PartInstalled(section)
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
                self.configuration[name],
                install_set,
                self.install_deps_directory)
            self.parts.append(part)

    def run(self):
        __status__ = u"Preparing installation."
        # Organise recipe order

        # Prepare recipe
        for part in self.parts:
            part.prepare()

        # Look for update/uninstall/install
        # - Copy, don't uninstall the old one.
        # - Move, reinstall all things.

        # - Uninstall remove parts
        # - Install added parts

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
