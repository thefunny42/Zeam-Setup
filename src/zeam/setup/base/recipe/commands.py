
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
                    u"WARNING: Missing installed path %s.",
                    path)
                return False
        data = self._data
        for piece in path.split(os.path.sep):
            data = data.setdefault(piece, {})
        data[None] = {'added': added, 'directory': os.path.isdir(path)}
        self._len += 1
        return True

    def extend(self, paths, verify=True, added=True):
        all_added = True
        for path in paths:
            all_added = self.add(path, verify=verify, added=added) and all_added
        return all_added

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

    def as_list(self, simplify=False, matches={}, prefixes={}):
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

        if prefixes:
            for path, replace in prefixes.iteritems():
                data = self._data
                for piece in path.split(os.path.sep):
                    data = data.get(piece)
                    if data is None:
                        break
                else:
                    build([replace], data)
        else:
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


class PartStatus(object):

    def __init__(self, section, installer):
        setup = section.configuration['setup']
        self._name = section.name
        self._installed_name = 'installed:' + self._name
        self._prefix = setup['prefix_directory'].as_text()
        self.requirements = []
        self.packages = WorkingSet(no_defaults=True)
        self.paths = Paths()
        self.installed_paths = Paths()
        self.depends = set(section.get('depends', '').as_list())
        self.depends_paths = Paths()
        self.parts = installer.parts_status

        installed_cfg = section.utilities.get('installed')
        if installed_cfg is not None:
            # We have a previous configuration
            self._installed_section = installed_cfg.get(
                self._installed_name, None)
            if self._installed_section is not None:
                get = self._installed_section.get
                # The part is installed if an installed path is missing
                # Or depending paths are missing, or install prefix changed
                # Or the configuration changed.
                self._enabled = (
                    not (self.installed_paths.extend(
                            get('paths', '').as_list()) and
                         Paths().extend(get('depends', '').as_list()) and
                         installed_cfg.get(self._name, None) == section) or
                    installer.prefix_changed)
                # XXX Should reinstall in case of dependency change as well
            else:
                self._enabled = True

            # Register ourselves to be seen by other status
            installer.parts_status[section.name] = self
        else:
            # With no previous configuration, we are uninstalling.
            self._installed_section = section.configuration.get(
                self._installed_name, None)
            if self._installed_section is not None:
                self.installed_paths.extend(
                    self._installed_section.get('paths', '').as_list())
            self._enabled = True

    def enable(self):
        self._enabled = True

    def is_enabled(self):
        return self._enabled

    def save(self, configuration):
        if self.is_enabled():
            # Save new information
            section = Section(self._installed_name, configuration=configuration)
            if self.paths:
                section['paths'] = self.paths.as_list(
                    prefixes={self._prefix: '${setup:prefix_directory}'})
            if self.packages:
                #section['packages'] = self.packages.as_requirements()
                self.depends_paths.extend(
                    [p.path for p in self.packages.installed.values()
                     if p.path is not None],
                    verify=False)
            if self.depends_paths:
                section['depends'] = self.depends_paths.as_list(
                    prefixes={self._prefix: '${setup:prefix_directory}'})
        else:
            # Save old information
            section = self._installed_section.__copy__()
        configuration[self._installed_name] = section
        return section

    def __repr__(self):
        return '<%s for %s>' % (self.__class__.__name__, self._name)


class Part(object):

    def __init__(self, section, installer):
        logger.warn('Load installation for %s' % section.name)
        self.name = section.name
        self.recipes = []
        self.status = PartStatus(section, installer)
        self.installer = installer

        for recipe in section['recipe'].as_list():
            try:
                factory = self.installer.get_recipe_entry_point(
                    'setup_installers', recipe)
            except PackageNotFound, error:
                # The package is not installed, install it and try again
                self.installer.add_recipe_packages([error.args[0]])
                factory = self.installer.get_recipe_entry_point(
                    'setup_installers', recipe)

            if factory is None:
                raise ConfigurationError(u"Could load recipe", recipe)
            self.recipes.append(factory(section, self.status))

    def __lt__(self, other):
        if not isinstance(other, Part):
            return NotImplemented
        if self.name in other.status.depends:
            return True
        return False

    def prepare(self):
        # Verify dependencies first.
        if self.status.is_enabled():
            logger.warn(u'Prepare installation for %s.', self.name)
            if self.status.requirements:
                self.installer.add_recipe_packages(self.status.requirements)
            for recipe in self.recipes:
                recipe.prepare()
        else:
            logger.warn(u'Nothing to prepare for %s.', self.name)

    def install(self):
        if self.status.is_enabled():
            logger.warn(u'Install %s.', self.name)
            for recipe in self.recipes:
                recipe.install()
        else:
            logger.warn(u'Nothing to install for %s.', self.name)

    def uninstall(self):
        if self.status.is_enabled():
            logger.warn(u'Uninstall %s.', self.name)
            for recipe in reversed(self.recipes):
                # We execute the recipes in reverse order here.
                recipe.uninstall()
        else:
            logger.warn(u'Nothing to unstall for %s.', self.name)

    def finalize(self, configuration):
        self.status.save(configuration)

    def __repr__(self):
        return '<%s for %s>' % (self.__class__.__name__, self.name)


class InstallerStatus(object):
    """Keep and update status for an installer.
    """

    def __init__(self, configuration):
        # Store all parts status for mutual access
        self.parts_status = {}

        # Look which parts must installed
        self._setup = configuration['setup']
        to_install_names = set(self._setup['install'].as_list())

        # Look previous configuration
        installed_cfg = configuration.utilities.installed
        installed_setup = installed_cfg.get('setup', None)
        if installed_setup is not None:
            self.prefix_changed = (
                self._setup['prefix_directory'].as_text() !=
                installed_setup['prefix_directory'].as_text())
            if self.prefix_changed:
                # Set prefix in previous configuration to the new not to
                # confuse installed paths.
                installed_setup['prefix_directory'].set_value(
                    self._setup['prefix_directory'].as_text())
            # Look what should be uninstalled
            to_uninstall_names = set(installed_setup['install'].as_list())
            to_uninstall_names -= to_install_names
        else:
            self.prefix_changed = False
            to_uninstall_names = []

        self.to_uninstall = [
            (name, installed_cfg[name]) for name in to_uninstall_names]
        self.to_install = [
            (name, configuration[name]) for name in to_install_names]

        # Setup working set: used only for recipes
        self._install_set = WorkingSet()
        self._install_directory = tempfile.mkdtemp('zeam.setup.install')
        self._installer = PackageInstaller(self._setup, self._install_set)
        self.get_recipe_entry_point = self._install_set.get_entry_point

    def add_recipe_packages(self, names):
        # This must be used only to install recipe and recipe dependency.
        install_set = self._installer(
            Requirements.parse(names),
            directory=self._install_directory)
        for name in names:
            install_set.get(name).activate()

    def verify_dependencies(self):
        cache = dict()
        markers = set()
        partitions = dict()

        def explore(name, is_top=False):
            if name in markers:
                raise ConfigurationError(
                    u"Circular dependencies detected between parts", name)
            if name not in cache:
                group = cache[name] = [name]
                markers.add(name)
                for depend in self.parts_status[name].depends:
                    if depend not in self.parts_status:
                        raise ConfigurationError(
                            u"Depends on missing part", name, depend)
                    all_depends, is_cached = explore(depend)
                    if is_cached:
                        if depend in partitions:
                            del partitions[depend]
                    group.extend(all_depends)
                markers.remove(name)
                if is_top:
                    partitions[name] = group
                return (group, False)
            return (cache[name], True)

        map(lambda name: explore(name, True), self.parts_status.keys())

        # Enable partitions that at leat a part enabled.
        for partition in partitions.values():
            for name in partition:
                if self.parts_status[name].is_enabled():
                    break
            else:
                continue
            for name in partition:
                self.parts_status[name].enable()

    def finalize(self):
        # Remove unused software.
        shutil.rmtree(self._install_directory)


class Installer(object):
    """Install an environment.
    """

    def __init__(self, configuration):
        __status__ = u"Loading installation recipes."
        self.configuration = configuration

        # Lookup parts
        self.status = InstallerStatus(configuration)
        self.parts_to_uninstall = []
        for name, section in self.status.to_uninstall:
            part = Part(section, self.status)
            self.parts_to_uninstall.append(part)
        self.parts_to_install = []
        for name, section in self.status.to_install:
            part = Part(section, self.status)
            self.parts_to_install.append(part)

        # Organize recipe
        self.status.verify_dependencies()

        # Uninstall are in reverse order of dependency informatiom
        self.parts_to_uninstall.sort(reverse=True)
        # Install are in order of dependency informations
        self.parts_to_install.sort()

    def run(self):
        # Prepare recipe
        __status__ = u"Preparing installation."
        for part in self.parts_to_install:
            part.prepare()

        # Uninstall what you need to uninstall first.
        __status__ = u"Running un-installation."
        for part in self.parts_to_uninstall:
            part.uninstall()

        # Install
        __status__ = u"Running installation."
        for part in self.parts_to_install:
            part.install()

        # Save status
        __status__ = u"Finalize installation."
        for part in self.parts_to_install:
            part.finalize(self.configuration)

        self.status.finalize()
