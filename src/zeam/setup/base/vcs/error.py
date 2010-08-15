
from zeam.setup.base.error import ConfigurationError, InstallationError


class VCSConfigurationError(ConfigurationError):
    """Error while quering for a VCS.
    """
    name = u"VCS Configuration Error"



class VCSError(InstallationError):
    """VCS error.
    """
    name = u"VCS Error"


class GitError(VCSError):
    """Git error.
    """
    name = u"Git Error"
