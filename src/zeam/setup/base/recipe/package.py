
import os
import operator

from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.utils import get_package_name, get_option_with_default
from zeam.setup.base.version import Requirements
from zeam.setup.base.distribution.workingset import WorkingSet
from zeam.setup.base.installer import PackageInstaller

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
    working_set, package_name, directory, args=None, wanted=None):
    created_scripts = []
    scripts = working_set.list_entry_points('console_scripts', package_name)

    args = ', '.join(args)

    for script_name, entry_point in scripts.items():
        if wanted and script_name not in wanted:
            continue
        package, callable = entry_point['destination'].split(':')
        script_path = os.path.join(directory, script_name)
        script_body = SCRIPT_BODY % {
            'args': args, 'package': package, 'callable': callable}
        created_scripts.append(
            working_set.create_script(script_path, script_body))
    return created_scripts


class Package(Recipe):
    """Install console_scripts of a package.
    """

    def __init__(self, configuration):
        super(Package, self).__init__(configuration)

        if 'packages' not in configuration:
            self.packages = [get_package_name(configuration).as_text()]
        else:
            self.packages = configuration['packages'].as_list()

        self.wanted = []
        if 'scripts' in configuration:
            self.wanted = configuration['scripts'].as_list()

        self.args = []
        if 'args' in configuration:
            self.args = configuration['args'].as_list()

    def install(self):
        directory = get_option_with_default(
            'bin_directory', self.configuration).as_text()
        working_set = WorkingSet(get_option_with_default(
                'python_executable', self.configuration).as_text())
        installer = PackageInstaller(self.configuration, working_set)
        installer(Requirements.parse(self.packages))
        create_scripts = lambda p: install_scripts(
            working_set, p, directory, self.args, self.wanted)
        return reduce(operator.add, map(create_scripts, self.packages))

    def uninstall(self):
        pass



class Interpreter(Package):
    """Create an python interpreter able to run the current
    environment.
    """

    def install(self):
        directory = get_option_with_default(
            'bin_directory', self.configuration).as_text()
        python_executable = get_option_with_default(
                'python_executable', self.configuration).as_text()
        working_set = WorkingSet(python_executable)
        installer = PackageInstaller(self.configuration, working_set)
        installer(Requirements.parse(self.packages))
        script_path = os.path.join(directory, self.configuration.name)
        return [working_set.create_script(script_path, INTERPRETER_BODY)]

    def uninstall(self):
        pass

