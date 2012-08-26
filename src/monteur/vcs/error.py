
from monteur.error import ConfigurationError, InstallationError


class VCSConfigurationError(ConfigurationError):
    """Error while quering for a VCS.
    """
    name = u"VCS configuration error"


class VCSError(InstallationError):
    """VCS error.
    """
    name = u"VCS error"


class GitError(VCSError):
    """Git error.
    """
    name = u"Git error"


class MercurialError(VCSError):
    """Mercurial error.
    """
    name = u"Mercurial error"


class SubversionError(VCSError):
    """Subversion error.
    """
    name = u"Subversion error"
