
from zeam.setup.base.vcs.vcs import VCSRegistry
from zeam.setup.base.vcs.subversion import SubversionFactory
from zeam.setup.base.vcs.git import GitFactory

VCS = VCSRegistry({'svn': SubversionFactory(),
                   'git': GitFactory()})
