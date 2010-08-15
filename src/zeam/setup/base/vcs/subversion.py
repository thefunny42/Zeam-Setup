
import subprocess

from zeam.setup.base.vcs.vcs import VCS, VCSFactory
from zeam.setup.base.utils import have_cmd


class Subversion(VCS):

    def checkout(self):
        subprocess.Popen(['svn', 'co', self.uri, self.directory])


class SubversionFactory(VCSFactory):
    name = 'subversion'

    def __init__(self):
        self.__available = have_cmd('svn', '--version')

    def available(self):
        return self.__available

    def __call__(self, uri, directory):
        return Subversion(uri, directory)


