
import logging

from zeam.setup.base.distribution.workingset import WorkingSet
from zeam.setup.base.configuration import Section
from zeam.setup.base.error import ConfigurationError

logger = logging.getLogger('zeam.setup')


class Installer(object):
    """Install an environment.
    """

    def __init__(self, configuration):
        __status__ = u"Loading installation recipes."
        self.configuration = configuration
        # Setup env
        releases = WorkingSet()

        # Lookup recipes
        self.recipes = {}
        setup = configuration['setup']
        for section_name in setup['install'].as_list():
            section = self.configuration[section_name]
            recipe_name = section['recipe'].as_text()
            recipe_factory = releases.get_entry_point(
                'setup_installers', recipe_name)
            if recipe_factory is None:
                raise ConfigurationError(u"Could load recipe", recipe_name)
            self.recipes[section_name] = recipe_factory(section)


    def run(self):
        __status__ = u"Preparing installation recipes."
        # Organise recipe order
        # Look for update/uninstall/install

        # Prepare recipe
        for recipe in self.recipes.values():
            section_name = 'installed:' + recipe.configuration.name
            installed_section = Section(section_name)
            self.configuration[section_name] = installed_section
            installed_section = self.configuration[section_name]

            recipe.prepare()

        # Uninstall in reverse order of install
        # Update
        # Install in order
        __status__ = u"Running installation recipes."
        for recipe in self.recipes.values():
            installed_path = recipe.install()
            installed_section['path'] = installed_path

