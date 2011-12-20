
class Recipe(object):
    """Install a part of the software.
    """

    def __init__(self, options, status):
        self.options = options
        self.status = status

    def preinstall(self):
        pass

    def install(self):
        pass

    def preuninstall(self):
        pass

    def uninstall(self):
        pass
