

class InstallationError(Exception):
    """Installation happening while installation.
    """

    name = u'Installation error'

    def __init__(self, *args):
        self.args = args

    def msg(self):
        return u': '.join((self.name, ) + self.args)

    __str__ = msg

class PackageError(InstallationError):
    """An error occurring while processing a package.
    """

    name = u'Package error'


class ConfigurationError(InstallationError):
    """Configuration error.
    """

    name = u'Configuration error'


class FileError(ConfigurationError):
    """Error while accesing a file.
    """

    name = u"File error"
