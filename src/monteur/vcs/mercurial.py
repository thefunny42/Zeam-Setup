

import logging

from monteur.utils import have_cmd, get_cmd_output, compare_uri
from monteur.vcs.error import MercurialError
from monteur.vcs.vcs import VCS, VCSFactory

logger = logging.getLogger('monteur')


class Mercurial(VCS):

    def __init__(self, checkout, options=[]):
        super(Mercurial, self).__init__(checkout, options=options)
        # Support for branch names as '#' in URL.
        if '#' in checkout.uri:
            uri, branch = checkout.uri.split('#', 1)
            if checkout.branch is not None and branch != checkout.branch:
                raise MercurialError(
                    u"Different branches are given in the URI and as option",
                    checkout.uri, checkout.branch)
            checkout.uri = uri
            checkout.branch = branch
        if checkout.branch is None:
            checkout.branch = 'default'

    def _run_mercurial(self, arguments, error=None, path=None):
        command = ['hg']
        command.extend(arguments)
        command.extend(['--quiet', '--noninteractive'])
        options = dict(path=path)
        stdout, stderr, code = get_cmd_output(*command, **options)
        if code:
            if error is None:
                error = u"Error while running mercurial command for"
            if code != 1 and (not stderr or stderr.startswith('warning:')):
                raise MercurialError(
                    error,  self.checkout.uri, command=command, detail=stderr)
        return stdout.strip()

    def fetch(self):
        self._run_mercurial(
            ['clone', self.checkout.uri, self.checkout.directory],
            error=u"Error while cloning")
        if self.checkout.branch != 'default':
            self.switch()

    def update(self):
        self._run_mercurial(
            ['pull', '-u'],
            path=self.checkout.directory,
            error=u"Error while pulling")

    def verify(self):
        current_uri = self._run_mercurial(
            ['showconfig', 'paths.default'],
            path=self.checkout.directory,
            error=u"Error while reading the current repository path")
        if '#' in current_uri:
            current_uri = current_uri.split('#', 1)[0]
        if not compare_uri(current_uri, self.checkout.uri):
            raise MercurialError(
                u"Cannot switch to a different repository.")
        current_branch = self._run_mercurial(
            ['branch'],
            path=self.checkout.directory,
            error=u"Error while reading the current branch")
        if self.checkout.branch != current_branch:
            return False
        return True

    def status(self):
        changes = self._run_mercurial(
            ['status'],
            path=self.checkout.directory,
            error=u"Error while checking for changes")
        return not len(changes)

    def switch(self):
        self._run_mercurial(
            ['update', '-r', 'branch(%r)' % self.checkout.branch],
            path=self.checkout.directory,
            error=u"Error while switching branch")


class MercurialPre17(Mercurial):

    def switch(self):
        self._run_mercurial(
            ['update', self.checkout.branch],
            path=self.checkout.directory,
            error=u"Error while switching branch")


class MercurialFactory(VCSFactory):
    software_name = 'mercurial'

    def __init__(self):
        self.available, self.version = have_cmd('hg', '--version')
        if isinstance(self.version, str):
            logger.info('Found Mercurial version %s' % self.version)

    def __call__(self, checkout):
        if self.version < '1.7':
            logger.error(
                u"Using an *old* mercurial version, "
                u"we recommand you to upgrade your Mercurial.")
            return MercurialPre17(checkout)
        return Mercurial(checkout)
