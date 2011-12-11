
import re
import os

from zeam.setup.base.distribution.workingset import WorkingSet
from zeam.setup.base.error import ConfigurationError
from zeam.setup.base.installer import PackageInstaller
from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.utils import get_package_name
from zeam.setup.base.version import Requirements

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


def install_scripts(
    working_set, package_name, directory,
    extra_args=[], wanted_scripts=None, extra_paths=[]):
    created_scripts = []
    scripts = working_set.list_entry_points('console_scripts', package_name)

    args = ', '.join(extra_args)

    for script_name, entry_point in scripts.items():
        if wanted_scripts is not None and script_name not in wanted_scripts:
            continue
        package, callable = entry_point['destination'].split(':')
        script_path = os.path.join(directory, script_name)
        script_body = SCRIPT_BODY % {
            'args': args, 'package': package, 'callable': callable}
        created_scripts.append(
            working_set.create_script(script_path, script_body, extra_paths))
    return created_scripts


class Package(Recipe):
    """Install console_scripts of a package.
    """

    def __init__(self, options):
        super(Package, self).__init__(options)

        self.directory = options.get(
            'directory',
            '${setup:lib_directory}').as_text()

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
            self.recipe_requires.update(self.extra_sets)

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

    def prepare(self, status):
        __status__ = u"Install required packages."
        self.working_set = WorkingSet(
            interpretor=self.options.get_with_default(
                'python_executable', 'setup').as_text(),
            no_defaults=True)
        if self.extra_sets:
            for name in self.extra_sets:
                if name not in status.parts:
                    raise ConfigurationError(
                        u"Specified part doesn't exists", name)
                self.working_set.extend(status.parts[name].packages)
                status.packages.extend(status.parts[name].packages)
        if self.requirements:
            installer = PackageInstaller(self.options, self.working_set)
            status.packages.extend(installer(self.requirements, self.directory))

    def install(self, status):
        __status__ = u"Install required scripts."
        bin_directory = self.options.get_with_default(
            'bin_directory', 'setup').as_text()
        create_scripts = lambda p: status.paths.extend(
            install_scripts(
                self.working_set, p.name, bin_directory,
                extra_args=self.extra_args,
                wanted_scripts=self.wanted_scripts,
                extra_paths=self.extra_paths))
        map(create_scripts, self.requirements)


class Interpreter(Package):
    """Create an python interpreter able to run the current
    environment.
    """

    def install(self, status):
        bin_directory = self.options.get_with_default(
            'bin_directory', 'setup').as_text()
        status.paths.add(
            self.working_set.create_script(
                os.path.join(bin_directory, self.options.name),
                INTERPRETER_BODY,
                extra_paths=self.extra_paths))


