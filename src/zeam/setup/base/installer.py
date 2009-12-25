
import logging
import os
import sys

from zeam.setup.base.configuration import Section
from zeam.setup.base.distribution import Environment, DevelopmentRelease
from zeam.setup.base.error import InstallationError

logger = logging.getLogger('zeam.setup')


class Installer(object):
    """Install an environment.
    """

    def __init__(self, config, environment):
        self.config = config
        # Setup env
        self.environment = environment

        # Lookup recipes
        self.recipes = {}
        setup = config['setup']
        for section_name in setup['install'].as_list():
            section = self.config[section_name]
            recipe_factory = self.environment.get_entry_point(
                'setup_installers', section['recipe'].as_text())
            self.recipes[section_name] = recipe_factory(
                self.environment, section)


    def run(self):
        # Organise recipe order
        # Look for update/uninstall/install

        # Prepare recipe
        # Uninstall in reverse order of install
        # Update
        # Install in order
        for recipe in self.recipes.values():
            section_name = 'installed:' + recipe.config.name
            installed_section = Section(section_name)
            self.config[section_name] = installed_section
            installed_section = self.config[section_name]

            recipe.prepare()

        for recipe in self.recipes.values():
            installed_path = recipe.install()
            installed_section['path'] = installed_path

