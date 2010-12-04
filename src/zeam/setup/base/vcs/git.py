
import logging

from zeam.setup.base.utils import have_cmd, get_cmd_output
from zeam.setup.base.vcs.vcs import VCS, VCSFactory
from zeam.setup.base.vcs.error import GitError

logger = logging.getLogger('zeam.setup')


class Git(VCS):

    def checkout(self):
        stdout, stderr, returncode = get_cmd_output(
            'git', 'clone', '--quiet', self.uri, self.directory)
        if returncode:
            raise GitError(u"Error while cloning %s" % self.uri)

    def update(self):
        stdout, stderr, returncode = get_cmd_output(
            'git', 'pull', path=self.directory)
        if returncode:
            raise GitError(u"Error while pulling %s" % self.uri)


class GitFactory(VCSFactory):
    package_name = 'git-core'

    def __init__(self):
        self.__available, self.__version = have_cmd('git', '--version')
        if isinstance(self.__version, str):
            logger.info('Found Git version %s' % self.__version)

    def available(self):
        return self.__available

    def __call__(self, uri, directory):
        return Git(uri, directory)
