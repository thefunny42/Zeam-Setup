
import logging
import os
import sys

from zeam.setup.base.distribution import Environment, DevelopmentRelease
from zeam.setup.base.error import InstallationError

logger = logging.getLogger('zeam.setup')


def create_directory(directory):
    directory = directory.strip()
    if not os.path.isdir(directory):
        logger.info('Creating directory %s' % directory)
        os.makedirs(directory)


def setup_environment(config, options):
    setup = config['setup']
    setup['bin_directory'].register(create_directory)
    setup['lib_directory'].register(create_directory)
    setup['log_directory'].register(create_directory)
    setup['var_directory'].register(create_directory)

    # Lookup python executable
    if 'python_executable' not in setup:
        setup['python_executable'] = sys.executable

    # Create an environment with develop packages
    environment = Environment()
    if 'develop' in setup:
        for path in setup['develop'].as_list():
            environment.add(DevelopmentRelease(path))
    return environment


class Installer(object):
    """Installer.
    """

    def __init__(self, config, options):
        self.config = config
        # Setup env
        self.environment = setup_environment(config, options)

        # Lookup recipes
        self.recipes = {}
        setup = config['setup']
        for section_name in setup['install'].as_list():
            section = self.config[section_name]
            recipe_factory = self.environment.get_entry_point(
                'zeam_installer', section['recipe'].as_text())
            self.recipes[section_name] = recipe_factory(
                self.environment, section)


    def run(self):
        for recipe in self.recipes.values():
            recipe.prepare()
            recipe.install()



