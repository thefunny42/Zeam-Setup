
import logging

from zeam.setup.base.utils import have_cmd, get_cmd_output
from zeam.setup.base.vcs.vcs import VCS, VCSFactory
from zeam.setup.base.vcs.error import GitError

logger = logging.getLogger('zeam.setup')


class Git(VCS):

    def _run_git(self, arguments, error=None, path=None):
        command = ['git']
        command.extend(arguments)
        stdout, stderr, code = get_cmd_output(*command, path=path)
        if code:
            logger.info(stderr)
            if error is None:
                error = u"Error while running git command for"
            raise GitError(error,  self.package.uri)
        return stdout

    def checkout(self):
        self._run_git(
            ['clone', '--quiet', self.package.uri, self.package.directory],
            error=u"Error while cloning.")

    def update(self):
        self._run_git(
            ['pull'],
            path=self.package.directory,
            error=u"Error while pulling.")

    def verify(self):
        current_uris = self._run_git(
            ['remote', '-v'])
        if self.package.uri not in current_uris:
            raise GitError(u"Cannot switch to a different repository.")

    def status(self):
        changes = self._run_git(
            ['status', '--porcelain'])
        return bool(len(changes.strip()))


class GitPre17(Git):

    def status(self):
        return True


class GitFactory(VCSFactory):
    software_name = 'git-core'

    def __init__(self):
        self.available, self.version = have_cmd('git', '--version')
        if isinstance(self.version, str):
            logger.info('Found Git version %s' % self.version)

    def __call__(self, package):
        if self.version < '1.7':
            logger.error(
                u"Using an *old* git version, "
                u"we recommand you to upgrade your Git setup.")
            return GitPre17(package)
        return Git(package)
