
class Recipe(object):
    """Install a part of the software.
    """
    requirements = []

    def __init__(self, options):
        self.options = options

    def prepare(self, status):
        pass

    def install(self, status):
        pass

    def uninstall(self, status):
        pass

    def update(self, status):
        pass
