

import logging

from zeam.setup.base.utils import have_cmd, get_cmd_output
from zeam.setup.base.vcs.error import MercurialError
from zeam.setup.base.vcs.vcs import VCS, VCSFactory

logger = logging.getLogger('zeam.setup')


class Mercurial(VCS):

    def checkout(self):
        stdout, stderr, returncode = get_cmd_output(
            'hg', 'clone', self.uri, self.directory)
        if returncode:
            raise MercurialError(u"Error while cloning %s" % self.uri)

    def update(self):
        stdout, stderr, returncode = get_cmd_output(
            'hg', 'pull', '-u', path=self.directory)
        if returncode:
            raise MercurialError(u"Error while pulling %s" % self.uri)


class MercurialFactory(VCSFactory):
    package_name = 'mercurial'

    def __init__(self):
        self.__available, self.__version = have_cmd('hg', '--version')
        if isinstance(self.__version, str):
            logger.info('Found Mercurial version %s' % self.__version)

    def avaiable(self):
        return self.__available

    def __call__(self, uri, directory):
        return Mercurial(uri, directory)
