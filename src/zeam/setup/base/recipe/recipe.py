
class Recipe(object):
    """Install a part of the software.
    """
    requirements = []

    def __init__(self, configuration):
        self.configuration = configuration

    def prepare(self, status):
        pass

    def install(self, status):
        pass

    def uninstall(self, status):
        pass

    def update(self, status):
        pass
