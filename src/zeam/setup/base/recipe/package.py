
import os

from zeam.setup.base.distribution.workingset import WorkingSet
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

    def __init__(self, configuration):
        super(Package, self).__init__(configuration)

        self.directory = configuration.get(
            'directory',
            '${setup:lib_directory}').as_text()

        if 'packages' not in configuration:
            self.packages = [get_package_name(configuration).as_text()]
        else:
            self.packages = configuration['packages'].as_list()

        self.wanted_scripts = None
        if 'scripts' in configuration:
            self.wanted_scripts = configuration['scripts'].as_list()

        self.extra_args = []
        if 'extra_args' in configuration:
            self.extra_args = configuration['extra_args'].as_list()

        self.extra_paths = []
        if 'extra_paths' in configuration:
            self.extra_paths = configuration['extra_paths'].as_list()

        self.working_set = None

    def prepare(self, status):
        __status__ = u"Install required packages."
        self.working_set = WorkingSet(
            self.configuration.get_with_default(
                'python_executable', 'setup').as_text())
        installer = PackageInstaller(self.configuration, self.working_set)
        status.add_packages(
            installer(Requirements.parse(self.packages), self.directory))

    def install(self, status):
        __status__ = u"Install required scripts."
        bin_directory = self.configuration.get_with_default(
            'bin_directory', 'setup').as_text()
        create_scripts = lambda p: status.add_paths(
            install_scripts(
                self.working_set, p, bin_directory,
                extra_args=self.extra_args,
                wanted_scripts=self.wanted_scripts,
                extra_paths=self.extra_paths))
        map(create_scripts, self.packages)


class Interpreter(Package):
    """Create an python interpreter able to run the current
    environment.
    """

    def install(self, status):
        bin_directory = self.configuration.get_with_default(
            'bin_directory', 'setup').as_text()
        script_path = os.path.join(bin_directory, self.configuration.name)
        status.add_path(
            self.working_set.create_script(
                script_path, INTERPRETER_BODY, extra_paths=self.extra_paths))


