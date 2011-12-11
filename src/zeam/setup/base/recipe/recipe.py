
class Recipe(object):
    """Install a part of the software.
    """
    recipe_requirements = []
    recipe_requires = set([])

    def __init__(self, options):
        self.options = options
        self.recipe_requires.update(options.get('requires', '').as_list())

    def prepare(self, status):
        pass

    def install(self, status):
        pass

    def uninstall(self, status):
        pass

    def update(self, status):
        pass
