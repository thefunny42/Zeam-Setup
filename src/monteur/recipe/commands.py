
import shutil
import tempfile
import logging

from monteur.sources import STRATEGY_UPDATE, STRATEGY_QUICK
from monteur.distribution.workingset import ReleaseSet, WorkingSet
from monteur.configuration import Section
from monteur.error import ConfigurationError, PackageNotFound
from monteur.installer import PackageInstaller
from monteur.version import Requirements
from monteur.recipe.utils import Paths

logger = logging.getLogger('monteur')


class PartStatus(object):

    def __init__(self, section, installer, strategy=STRATEGY_UPDATE):
        setup = section.configuration['setup']
        self._name = section.name
        self._installed_name = 'installed:' + self._name
        self._prefix = setup['prefix_directory'].as_text()
        self.requirements = []
        self.packages = ReleaseSet()
        self.paths = Paths()
        self.installed_paths = Paths()
        self.depends = set(section.get('depends', '').as_list())
        self.depends_paths = Paths()
        self.parts = installer.parts_status
        self.strategy = strategy

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

    def enable(self, flag=True):
        if flag:
            self._enabled = True

    def is_enabled(self):
        return self._enabled

    def save(self, configuration):
        if self.is_enabled():
            # Save new information
            section = Section(self._installed_name, configuration=configuration)
            if self.paths:
                section['paths'] = self.paths.as_list(
                    replaces={self._prefix: '${setup:prefix_directory}'})
            if self.packages:
                #section['packages'] = self.packages.as_requirements()
                self.depends_paths.extend(
                    [p.path for p in self.packages
                     if p.path is not None],
                    verify=False)
            if self.depends_paths:
                section['depends'] = self.depends_paths.as_list(
                    replaces={self._prefix: '${setup:prefix_directory}'})
        else:
            # Save old information
            section = self._installed_section.__copy__()
        configuration[self._installed_name] = section
        return section

    def __repr__(self):
        return '<%s for %s>' % (self.__class__.__name__, self._name)


class Part(object):

    def __init__(self, section, installer, strategy=STRATEGY_UPDATE):
        logger.warn('Load installation for %s.' % section.name)
        self.name = section.name
        self.recipes = []
        self.status = PartStatus(section, installer, strategy)
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

    def preinstall(self):
        # Verify dependencies first.
        if self.status.is_enabled():
            logger.warn(u'Prepare installation for %s.', self.name)
            if self.status.requirements:
                self.installer.add_recipe_packages(self.status.requirements)
            for recipe in self.recipes:
                recipe.preinstall()
            return True
        logger.warn(u'Nothing to prepare for %s.', self.name)
        return False

    def install(self):
        if self.status.is_enabled():
            logger.warn(u'Install %s.', self.name)
            for recipe in self.recipes:
                recipe.install()
            return True
        logger.warn(u'Nothing to install for %s.', self.name)
        return False

    def preuninstall(self):
        if self.status.is_enabled():
            logger.warn(u'Pre-uninstall %s.', self.name)
            for recipe in reversed(self.recipes):
                # We execute the recipes in reverse order here.
                recipe.preuninstall()
            return True
        logger.warn(u'Nothing to pre-uninstall for %s.', self.name)
        return False

    def uninstall(self):
        if self.status.is_enabled():
            logger.warn(u'Uninstall %s.', self.name)
            for recipe in reversed(self.recipes):
                # We execute the recipes in reverse order here.
                recipe.uninstall()
            return True
        logger.warn(u'Nothing to uninstall for %s.', self.name)
        return False

    def finalize(self, configuration):
        self.status.save(configuration)

    def __repr__(self):
        return '<%s for %s>' % (self.__class__.__name__, self.name)


class InstallerStatus(object):
    """Keep and update status for an installer.
    """

    def __init__(self, configuration, strategy):
        # Store all parts status for mutual access
        self.parts_status = {}
        self.strategy = strategy

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
        self._install_set = WorkingSet(no_activate=False)
        self._install_directory = tempfile.mkdtemp('monteur.install')
        self._installer = PackageInstaller(self._setup, self._install_set)
        self.get_recipe_entry_point = self._install_set.get_entry_point

    def add_recipe_packages(self, names):
        # This must be used only to install recipe and recipe dependency.
        requirements = Requirements.parse(names)
        install_set = self._installer(
            requirements,
            directory=self._install_directory,
            strategy=self.strategy)
        for requirement in requirements:
            install_set.get(requirement.key).activate()

    def verify_dependencies(self, refresh=False):
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

        if not refresh:
            # Enable partitions that at least a part enabled.
            for partition in partitions.values():
                for name in partition:
                    if self.parts_status[name].is_enabled():
                        break
                else:
                    continue
                for name in partition:
                    self.parts_status[name].enable()
        else:
            # Refresh enables all parts.
            for parts in self.parts_status.values():
                parts.enable()

    def finalize(self):
        # Remove unused software.
        shutil.rmtree(self._install_directory)


class Installer(object):
    """Install an environment.
    """

    def __init__(self, session):
        __status__ = u"Loading installation recipes."
        self.configuration = session.configuration

        refresh = 'refresh' in session.args or 'update' in session.args
        strategy = (STRATEGY_UPDATE in session.args and
                    STRATEGY_UPDATE or STRATEGY_QUICK)

        # Lookup parts
        self.status = InstallerStatus(session.configuration, strategy)
        self.parts_to_uninstall = []
        for name, section in self.status.to_uninstall:
            part = Part(section, self.status, strategy)
            self.parts_to_uninstall.append(part)
        self.parts_to_install = []
        for name, section in self.status.to_install:
            part = Part(section, self.status, strategy)
            self.parts_to_install.append(part)

        # Organize recipe
        self.status.verify_dependencies(refresh)

        # Uninstall are in reverse order of dependency informatiom
        self.parts_to_uninstall.sort(reverse=True)
        # Install are in order of dependency informations
        self.parts_to_install.sort()

    def run(self):
        changed = False

        # Prepare parts to install
        __status__ = u"Preparing installation."
        for part in self.parts_to_install:
            changed = part.preinstall() or changed

        # Prepare parts to install
        __status__ = u"Preparing un-installation."
        for part in self.parts_to_uninstall:
            changed = part.preuninstall() or changed

        # Uninstall what you need to uninstall first.
        __status__ = u"Running un-installation."
        for part in self.parts_to_uninstall:
            changed = part.uninstall() or changed

        # Install
        __status__ = u"Running installation."
        for part in self.parts_to_install:
            changed = part.install() or changed

        # Save status
        __status__ = u"Finalize installation."
        for part in self.parts_to_install:
            part.finalize(self.configuration)

        self.status.finalize()
        return changed
