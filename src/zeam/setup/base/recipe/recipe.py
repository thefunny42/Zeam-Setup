
from zeam.setup.base.version import Requirements
from zeam.setup.base.distribution.workingset import WorkingSet
from zeam.setup.base.installer import PackageInstaller

class Recipe(object):
    """Install a part of the software.
    """
    requirements = []

    def __init__(self, configuration):
        self.configuration = configuration
        if self.requirements:
            self._install_recipe_requirements(self.requirements)

    def _install_recipe_requirements(self, *requirements):
        __status__ = u"Installing recipe requirements: %s" % (requirements)
        working_set = WorkingSet()
        installer = PackageInstaller(self.configuration, working_set)
        installer(Requirements.parse(requirements))
        for requirement in requirements:
            working_set.get(requirement).activate()

    def install(self):
        pass

    def uninstall(self):
        pass

    def prepare(self):
        pass

    def update(self):
        pass
