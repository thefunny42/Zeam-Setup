
import logging

from zeam.setup.base.vcs.vcs import VCS, VCSFactory
from zeam.setup.base.utils import have_cmd, get_cmd_output
from zeam.setup.base.vcs.error import SubversionError

logger = logging.getLogger('zeam.setup')


class Subversion(VCS):

    def _build_command(self, *arguments):
        command = ['svn']
        command.extend(self.generic_options)
        command.extend(arguments)
        return command

    def checkout(self):
        command = self._build_command('co', self.uri, self.directory)
        stdout, stderr, returncode = get_cmd_output(*command)
        if returncode:
            raise SubversionError(u"Error while doing check out of  %s" % (
                    self.uri))

    def update(self):
        command = self._build_command('update')
        command_options = {'path': self.directory}
        stdout, stderr, returncode = get_cmd_output(*command, **command_options)
        if returncode:
            raise SubversionError(u"Error while updating %s" % self.uri)


class SubversionFactory(VCSFactory):
    package_name = 'subversion'

    def __init__(self):
        self.__available, self.__version = have_cmd('svn', '--version')
        if isinstance(self.__version, str):
            logger.info(u'Found Subversion version %s' % self.__version)
        self.__options = ['--non-interactive']
        if self.__version > '1.6':
            self.__options.append('--trust-server-cert')

    def available(self):
        return self.__available

    def __call__(self, uri, directory):
        return Subversion(uri, directory)


