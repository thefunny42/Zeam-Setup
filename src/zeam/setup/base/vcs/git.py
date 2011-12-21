
import logging

from zeam.setup.base.utils import have_cmd, get_cmd_output
from zeam.setup.base.vcs.vcs import VCS, VCSFactory
from zeam.setup.base.vcs.error import GitError

logger = logging.getLogger('zeam.setup')


class Git(VCS):

    def __init__(self, package, options=[]):
        super(Git, self).__init__(package, options=options)
        if package.branch is None:
            package.branch = 'master'

    def _run_git(self, arguments, error=None, path=None):
        command = ['git']
        command.extend(arguments)
        stdout, stderr, code = get_cmd_output(*command, path=path)
        if code:
            if error is None:
                error = u"Error while running git command for"
            raise GitError(
                error,  self.package.uri, command=command, detail=stderr)
        return stdout.strip()

    def checkout(self):
        self._run_git(
            ['clone', '--quiet', self.package.uri, self.package.directory],
            error=u"Error while cloning")

    def update(self):
        self._run_git(
            ['pull', '--quiet'],
            path=self.package.directory,
            error=u"Error while pulling")

    def verify(self):
        current_uris = self._run_git(
            ['remote', '-v'],
            path=self.package.directory)
        for current_uri in current_uris.splitlines():
            if self.package.uri in current_uri:
                break
        else:
            raise GitError(u"Cannot switch to a different repository")
        current_branchs = self._run_git(
            ['branch'],
            path=self.package.directory)
        for current_branch in current_branchs.splitlines():
            if current_branch.startswith('*'):
                branch_parts = current_branch.split()
                if len(branch_parts) < 2:
                    break
                if branch_parts[-1] != self.package.branch:
                    return False
                return True
        raise GitError(u"Cannot determine current branch")

    def status(self):
        changes = self._run_git(
            ['status', '--porcelain'],
            path=self.package.directory,
            error=u"Error while checking for changes")
        return not len(changes)

    def switch(self):
        pass

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
