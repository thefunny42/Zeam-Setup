
import logging
try:
    import xml.etree.ElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

from zeam.setup.base.vcs.vcs import VCS, VCSFactory
from zeam.setup.base.utils import have_cmd, get_cmd_output
from zeam.setup.base.vcs.error import SubversionError

logger = logging.getLogger('zeam.setup')
INVALID_CERTIFICATE = 'certificate verification failed: issuer is not trusted'
AUTHORIZATION_FAILED = 'authorization failed'


def read_info(xml):
    # Read the output of svn status in XML.
    try:
        dom = etree.fromstring(xml)
    except:
        return None, None
    entry = dom.find('entry')
    if entry is None:
        return None, None
    url = entry.find('url')
    if url is None:
        return None, None
    repository = entry.find('repository')
    if repository is None:
        return None, None
    root = repository.find('root')
    if root is None:
        return None, None
    return url.text.strip(), root.text.strip()


class Subversion(VCS):

    def _run_svn(self, arguments, error=None, path=None):
        command = ['svn']
        command.extend(self.options)
        command.extend(arguments)
        stdout, stderr, code = get_cmd_output(
            *command, environ={'LC_ALL': 'C'}, path=path)
        if code:
            logger.info(stderr)
            reason = stderr.strip().split('\n')[-1]
            if INVALID_CERTIFICATE in reason:
                raise SubversionError(
                    u"Invalid certificate. "
                    u"Please checkout and approve certificate by hand.",
                    self.package.uri)
            if AUTHORIZATION_FAILED in reason:
                raise SubversionError(
                    u"Invalid username or password",
                    self.package.uri)
            if error is None:
                error = u"Error while running svn command for"
            raise SubversionError(error, self.package.uri)
        return stdout

    def checkout(self):
        self._run_svn(
            ['co', self.package.uri, self.package.directory],
            error=u"Error while doing check out of")

    def update(self):
        self._run_svn(
            ['update'],
            path=self.package.directory,
            error=u"Error while updating")

    def verify(self):
        xml = self._run_svn(
            ['info', '--xml'],
            path=self.package.directory,
            error="Checkout directory is not a valid Subversion checkout")
        current_uri, current_root = read_info(xml)
        if current_uri is None:
            raise SubversionError(
                u"Could not read the output of Subversion",
                self.package.directory)
        if current_uri != self.package.uri:
            if not self.package.uri.startswith(current_root):
                raise SubversionError(
                    u"Cannot switch to a different Subversion repository",
                    current_root, self.package.uri)
            return False
        return True

    def switch(self):
        # XXX Verify uncommited changes first.
        self._run_svn(
            ['switch', self.package.uri],
            path=self.package.directory,
            error=u"Error cannot switch Subversion repository")


class SubversionFactory(VCSFactory):
    software_name = 'subversion'

    def __init__(self):
        self.available, self.version = have_cmd('svn', '--version')
        if isinstance(self.version, str):
            logger.info(u'Found Subversion version %s' % self.version)
        self.options = ['--non-interactive']
        if self.version > '1.6':
            self.options.append('--trust-server-cert')

    def __call__(self, package):
        return Subversion(package, options=self.options)


