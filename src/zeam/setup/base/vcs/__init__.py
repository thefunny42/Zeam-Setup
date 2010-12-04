
from zeam.setup.base.vcs.vcs import VCSRegistry, DevelopFactory
from zeam.setup.base.vcs.subversion import SubversionFactory
from zeam.setup.base.vcs.git import GitFactory
from zeam.setup.base.vcs.mercurial import MercurialFactory

VCS = VCSRegistry({'svn': SubversionFactory,
                   'git': GitFactory,
                   'hg': MercurialFactory,
                   'develop': DevelopFactory})
