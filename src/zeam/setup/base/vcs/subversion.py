
import subprocess

from zeam.setup.base.vcs.vcs import VCS
from zeam.setup.base.utils import have_cmd


class Subversion(VCS):

    def checkout(self):
        subprocess.Popen(['svn', 'co', self.uri, self.directory])

