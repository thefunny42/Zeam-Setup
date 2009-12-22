

class InstallationError(Exception):
    """Installation happening while installation.
    """

    name = u'Installation error'

    def msg(self):
        return u'%s: %s'% (self.name, str(self.args))


class ConfigurationError(InstallationError):
    """Configuration error.
    """

    name = u'Configuration error'

    def __init__(self, location, reason):
        InstallationError.__init__(self, location, reason)
        self.location = location
        self.reason = reason

    def msg(self):
        return u'%s: %s: %s' % (self.name, self.location, self.reason)


class FileError(ConfigurationError):
    """Error while accesing a file.
    """

    name = u"File error"
