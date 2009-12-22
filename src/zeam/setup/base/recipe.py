

class Recipe(object):
    """Install a part of the software.
    """

    def __init__(self, installer, config):
        self.installer = installer
        self.config = config

    def install(self):
        pass

    def uninstall(self):
        pass

    def prepare(self):
        pass

    def update(self):
        pass
