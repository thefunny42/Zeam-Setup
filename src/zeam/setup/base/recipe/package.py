
import os

from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.utils import get_package_name, get_option_with_default
from zeam.setup.base.version import Requirement


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


def install_scripts(environment, config, package_name, args=None, wanted=None):
    created_scripts = []
    scripts = environment.list_entry_points('console_scripts', package_name)
    python_executable = get_option_with_default(
        'python_executable', config).as_text()
    bin_directory = get_option_with_default(
        'bin_directory', config).as_text()

    args = ', '.join(args)

    for script_name, entry_point in scripts.items():
        if wanted and script_name not in wanted:
            continue
        package, callable = entry_point['destination'].split(':')
        script_path = os.path.join(bin_directory, script_name)
        script_body = SCRIPT_BODY % {
            'args': args, 'package': package, 'callable': callable,}
        created_scripts.append(environment.create_script(
                script_path, script_body, executable=python_executable))
    return created_scripts


class Package(Recipe):
    """Install console_scripts of a package.
    """

    def __init__(self, environment, config):
        super(Package, self).__init__(environment, config)

        if 'packages' not in config:
            self.packages = [get_package_name(config).as_text()]
        else:
            self.packages = config['packages'].as_list()

        self.wanted = []
        if 'scripts' in config:
            self.wanted = self.config['scripts'].as_list()

        self.args = []
        if 'args' in config:
            self.args = self.config['args'].as_list()

    def install(self):
        scripts = []
        for package in self.packages:
            self.environment.install(Requirement.parse(package))
            scripts.extend(install_scripts(
                    self.environment, self.config, package,
                    self.args, self.wanted))
        return scripts

    def uninstall(self):
        pass



class Interpreter(Recipe):
    """Create an python interpreter able to run the current
    environment.
    """

    def install(self):
        python_executable = get_option_with_default(
            'python_executable', self.config).as_text()
        bin_directory = get_option_with_default(
            'bin_directory', self.config).as_text()
        script_path = os.path.join(bin_directory, self.config.name)
        return [self.environment.create_script(
                script_path, INTERPRETER_BODY, executable=python_executable)]

    def uninstall(self):
        pass
