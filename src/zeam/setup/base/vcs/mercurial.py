

import logging

from zeam.setup.base.utils import have_cmd, get_cmd_output, compare_uri
from zeam.setup.base.vcs.error import MercurialError
from zeam.setup.base.vcs.vcs import VCS, VCSFactory

logger = logging.getLogger('zeam.setup')


class Mercurial(VCS):

    def __init__(self, package, options=[]):
        super(Mercurial, self).__init__(package, options=options)
        # Support for branch names as '#' in URL.
        if '#' in package.uri:
            uri, branch = package.uri.split('#', 1)
            if package.branch is not None and branch != package.branch:
                raise MercurialError(
                    u"Different branches are given in the URI and as option",
                    package.uri, package.branch)
            package.uri = uri
            package.branch = branch
        if package.branch is None:
            package.branch = 'default'

    def _run_mercurial(self, arguments, error=None, path=None):
        command = ['hg']
        command.extend(arguments)
        command.extend(['--quiet', '--noninteractive'])
        stdout, stderr, code = get_cmd_output(*command, path=path)
        if code:
            if error is None:
                error = u"Error while running mercurial command for"
            raise MercurialError(
                error,  self.package.uri, command=command, detail=stderr)
        return stdout.strip()

    def checkout(self):
        self._run_mercurial(
            ['clone', self.package.uri, self.package.directory],
            error=u"Error while cloning")
        if self.package.branch != 'default':
            self.switch()

    def update(self):
        self._run_mercurial(
            ['pull', '-u'],
            path=self.package.directory,
            error=u"Error while pulling")

    def verify(self):
        current_uri = self._run_mercurial(
            ['showconfig', 'paths.default'],
            path=self.package.directory,
            error=u"Error while reading the current repository path")
        if '#' in current_uri:
            current_uri = current_uri.split('#', 1)[0]
        if not compare_uri(current_uri, self.package.uri):
            raise MercurialError(
                u"Cannot switch to a different repository.")
        current_branch = self._run_mercurial(
            ['branch'],
            path=self.package.directory,
            error=u"Error while reading the current branch")
        if self.package.branch != current_branch:
            return False
        return True

    def status(self):
        changes = self._run_mercurial(
            ['status'],
            path=self.package.directory,
            error=u"Error while checking for changes")
        return not len(changes)

    def switch(self):
        self._run_mercurial(
            ['update', '-r', 'branch(%r)' % self.package.branch],
            path=self.package.directory,
            error=u"Error while switching branch")


class MercurialPre17(Mercurial):

    def switch(self):
        self._run_mercurial(
            ['update', self.package.branch],
            path=self.package.directory,
            error=u"Error while switching branch")


class MercurialFactory(VCSFactory):
    software_name = 'mercurial'

    def __init__(self):
        self.available, self.version = have_cmd('hg', '--version')
        if isinstance(self.version, str):
            logger.info('Found Mercurial version %s' % self.version)

    def __call__(self, package):
        if self.version < '1.7':
            logger.error(
                u"Using an *old* mercurial version, "
                u"we recommand you to upgrade your Mercurial.")
            return MercurialPre17(package)
        return Mercurial(package)
