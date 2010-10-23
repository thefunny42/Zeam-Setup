

class Recipe(object):
    """Install a part of the software.
    """

    def __init__(self, configuration):
        self.configuration = configuration

    def install(self):
        pass

    def uninstall(self):
        pass

    def prepare(self):
        pass

    def update(self):
        pass
