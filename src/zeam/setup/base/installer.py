

class Installer(object):
    """Installer.
    """

    def __init__(self, recipes):
        self.recipes = recipes
        self.configuration = None

    def run(self):
        for recipe in self.recipes:
            recipe.prepare()



