

class VCS(object):
    """Base API to access a project in a VCS.
    """

    def __init__(self, uri, directory):
        self.uri = uri
        self.directory = directory

    def checkout(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()


