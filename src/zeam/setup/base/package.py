
import os

from zeam.setup.base.recipe import Recipe
from zeam.setup.base.utils import get_package_name, get_option_with_default


SCRIPT_BODY = """
import %(package)s

if __name__ == '__main__':
  %(package)s.%(callable)s(%(args)s)
"""


class Package(Recipe):
    """Install console_scripts of a package.
    """

    def __init__(self, environment, config):
        super(Package, self).__init__(environment, config)
        self.package_name = get_package_name(config).as_text()

    def install(self):
        created_scripts = []
        all_scripts = self.environment.list_entry_points(
            'console_scripts', self.package_name)
        python_executable = get_option_with_default(
            'python_executable', self.config).as_text()
        bin_directory = get_option_with_default(
            'bin_directory', self.config).as_text()

        wanted_scripts = self.config.get('scripts', None)
        if wanted_scripts is not None:
            wanted_scripts = wanted_scripts.as_list()

        args = self.config.get('arguments', None)
        if args is not None:
            args = ', '.join(args.as_list())
        else:
            args = ''

        for script_name, entry_point in all_scripts.items():
            if wanted_scripts is not None and script_name not in wanted_scripts:
                continue
            package, callable = entry_point['destination'].split(':')
            script_path = os.path.join(bin_directory, script_name)
            script_body = SCRIPT_BODY % {
                'args': args, 'package': package, 'callable': callable,}
            created_scripts.append(self.environment.create_script(
                script_path, script_body, executable=python_executable))

        return created_scripts

    def uninstall(self):
        pass
