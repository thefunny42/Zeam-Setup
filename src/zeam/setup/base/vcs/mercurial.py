

import logging

from zeam.setup.base.utils import have_cmd, get_cmd_output
from zeam.setup.base.vcs.error import MercurialError
from zeam.setup.base.vcs.vcs import VCS, VCSFactory

logger = logging.getLogger('zeam.setup')


class Mercurial(VCS):

    def _run_mercurial(self, arguments, error=None, path=None):
        command = ['hg']
        command.extend(arguments)
        command.extend(['--quiet', '--noninteractive'])
        stdout, stderr, code = get_cmd_output(*command, path=path)
        if code:
            logger.info(stderr)
            if error is None:
                error = u"Error while running mercurial command for"
            raise MercurialError(error,  self.package.uri)

    def checkout(self):
        self._run_mercurial(
            ['clone', self.package.uri, self.package.directory],
            error=u"Error while cloning")

    def update(self):
        self._run_mercurial(
            ['pull', '-u'],
            error=u"Error while pulling",
            path=self.package.directory)


class MercurialFactory(VCSFactory):
    software_name = 'mercurial'

    def __init__(self):
        self.available, self.version = have_cmd('hg', '--version')
        if isinstance(self.version, str):
            logger.info('Found Mercurial version %s' % self.version)

    def __call__(self, package):
        return Mercurial(package)
