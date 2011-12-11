
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

    def __init__(self, paths=None, verify=True):
        self._data = {}
        self._len = 0
        if paths:
            self.extend(paths, verify=verify)

    def add(self, path, verify=True, added=True):
        if verify:
            if not os.path.exists(path):
                logger.error(
                    u"WARNING: Missing installed path %s, ignore it",
                    path)
                return
        data = self._data
        for piece in path.split(os.path.sep):
            data = data.setdefault(piece, {})
        data[None] = {'added': added, 'directory': os.path.isdir(path)}
        self._len += 1

    def extend(self, paths, verify=True, added=True):
        for path in paths:
            self.add(path, verify=verify, added=added)

    def rename(self, old, new):

        def rename_sub(old_data, old_ids, new_data, new_ids):
            assert len(old_ids) == len(new_ids), \
                'Path of different depths are not supported'

            if not old_ids:
                if None not in old_data:
                    raise ValueError
                new_data[None] = old_data[None]
                del old_data[None]
                return len(old_data) == 0

            old_id = old_ids.pop(0)
            new_id = new_ids.pop(0)

            if old_id not in old_data:
                raise ValueError

            add_data = new_data.get(new_id, {})
            unique = len(old_data[old_id]) == 1

            prune = rename_sub(
                old_data[old_id], old_ids,
                add_data, new_ids)

            prune = unique and prune
            new_data[new_id] = add_data

            if old_id == new_id:
                return prune
            if prune:
                del old_data[old_id]
            return prune

        try:
            rename_sub(
                self._data, old.split(os.path.sep),
                self._data, new.split(os.path.sep))
            return True
        except ValueError:
            return False

    def get_added(self, directory=None):
        matches = {'added': True}
        if directory is not None:
            matches['directory'] = directory
        return self.as_list(True, matches=matches)

    def as_list(self, simplify=False, matches={}):
        result = []

        def build(prefix, data):
            for key, value in sorted(data.items(), key=operator.itemgetter(0)):
                if key is None:
                    for match_key, match_value in matches.items():
                        if value.get(match_key, None) != match_value:
                            break
                    else:
                        result.append(os.path.sep.join(prefix))
                        if simplify:
                            # None is always the smallest.
                            break
                else:
                    build(prefix + [key], value)

        build([], self._data)
        return result

    def __len__(self):
        return self._len

    def __contains__(self, path):
        data = self._data
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
