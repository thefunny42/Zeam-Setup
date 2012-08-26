
import logging
import os
import re

from monteur.distribution.workingset import WorkingSet
from monteur.error import ConfigurationError, InstallationError
from monteur.installer import PackageInstaller, is_installer_changed
from monteur.recipe.recipe import Recipe
from monteur.utils import get_package_name
from monteur.version import Requirements, Requirement

logger = logging.getLogger('monteur')

SCRIPT_BODY = """
import %(package)s

if __name__ == '__main__':
  %(package)s.%(callable)s(%(args)s)
"""

INTERPRETER_BODY = """
_interactive = True
if len(sys.argv) > 1:
    import getopt
    _options, _args = getopt.getopt(sys.argv[1:], 'ic:')
    _interactive = False
    for (_opt, _val) in _options:
        if _opt == '-i':
            _interactive = True
        elif _opt == '-c':
            exec _val

    if _args:
        sys.argv[:] = _args
        execfile(sys.argv[0])

if _interactive:
    import code
    code.interact(local=globals())
"""

INSTALLED_SET = re.compile(r'^\$<installed:(?P<name>[^>]+)>$')


class Package(Recipe):
    """Install console_scripts of a package.
    """

    def __init__(self, options, status):
        super(Package, self).__init__(options, status)
        self.isolation = options.get(
            'isolation', 'on').as_bool()
        self.directory = options.get(
            'lib_directory',
            '${setup:lib_directory}').as_text()
        self.bin_directory = options.get(
            'bin_directory',
            '${setup:bin_directory}').as_text()

        requirements = []
        self.extra_sets = []
        if 'packages' in options:
            for requirement in options['packages'].as_list():
                match = INSTALLED_SET.match(requirement)
                if match:
                    self.extra_sets.append(match.group('name'))
                else:
                    requirements.append(requirement)
        else:
            requirements = [get_package_name(options).as_text()]
        self.requirements = Requirements.parse(requirements)
        if self.extra_sets:
            status.depends.update(self.extra_sets)
        if self.requirements:
            # Run the recipe is installer settings changed.
            status.enable(is_installer_changed(options))

        self.wanted_scripts = None
        if 'scripts' in options:
            self.wanted_scripts = options['scripts'].as_list()
        self.extra_args = []
        if 'extra_args' in options:
            self.extra_args = options['extra_args'].as_list()
        self.extra_paths = []
        if 'extra_paths' in options:
            self.extra_paths = options['extra_paths'].as_list()

        self.working_set = None

    def preinstall(self):
        __status__ = u"Install required packages."
        self.working_set = WorkingSet(
            interpretor=self.options.get_with_default(
                'python_executable', 'setup').as_text(),
            no_defaults=True)
        if self.extra_sets:
            for name in self.extra_sets:
                if name not in self.status.parts:
                    raise ConfigurationError(
                        u"Specified part doesn't exists", name)
                self.working_set.extend(self.status.parts[name].packages)
                self.status.packages.extend(self.status.parts[name].packages)
        if self.isolation:
            self.requirements += Requirements(Requirement('zeam.site'))
        if self.requirements:
            installer = PackageInstaller(self.options, self.working_set)
            self.status.packages.extend(
                installer(
                    self.requirements,
                    self.directory,
                    self.status.strategy))
        logger.info(
            u'Installed %d packages (including Python) for "%s".',
            len(self.working_set), self.options.name)

    def create_scripts(self, requirement):
        wanted_scripts = []
        if self.wanted_scripts is not None:
            wanted_scripts = self.wanted_scripts
        scripts = self.working_set.list_entry_points(
            'console_scripts', requirement.key)
        args = ', '.join(self.extra_args)

        for script_name, entry_point in scripts.items():
            if script_name not in wanted_scripts:
                continue
            script_path = os.path.join(self.bin_directory, script_name)
            if script_path not in self.status.installed_paths:
                if os.path.exists(script_path):
                    raise InstallationError(
                        u"Script already exists", script_path)
            package, main = entry_point['destination'].split(':')
            script_body = SCRIPT_BODY % {
                'args': args, 'package': package, 'callable': main}
            self.status.paths.add(
                self.working_set.create_script(
                    script_path, script_body, extra_paths=self.extra_paths,
                    script_isolation=self.isolation),
                added=True)

    def install(self):
        __status__ = u"Install required scripts."
        map(self.create_scripts, self.requirements)

    def uninstall(self):
        __status__ = u"Uninstall scripts."
        for script in self.status.installed_paths.as_list():
            if os.path.isfile(script):
                os.remove(script)
            else:
                raise InstallationError(
                    u"Missing script while uninstalling", script)


class Interpreter(Package):
    """Create an python interpreter able to run the current
    environment.
    """

    def install(self):
        script_path = os.path.join(self.bin_directory, self.options.name)
        if script_path not in self.status.installed_paths:
            if os.path.exists(script_path):
                raise InstallationError(
                    u"Script already exists", script_path)

        self.status.paths.add(
            self.working_set.create_script(
                script_path, INTERPRETER_BODY,
                extra_paths=self.extra_paths, script_isolation=self.isolation),
            added=True)


