
import logging
import sys
import traceback

logger = logging.getLogger('zeam.setup')


def create_error_report(filename='error.log'):
    """Log last error in a file.
    """
    trace = sys.exc_info()[2]
    try:
        error_file = open(filename, 'w')
        traceback.print_tb(trace, None, error_file)
        error_file.close()
    except IOError:
        pass


def display_error(error):
    """Display the last error, and quit.
    """
    logger.critical(u'\nAn error happened:')
    exc_info = sys.exc_info()
    trace = exc_info[2]
    while trace is not None:
        locals = trace.tb_frame.f_locals
        if '__status__' in locals:
            logger.critical(u'While: %s' % locals['__status__'])
        trace = trace.tb_next

    create_error_report()
    logger.critical(error.msg())
    sys.exit(-1)


class InstallationError(Exception):
    """Installation happening while installation.
    """
    name = u'Installation error'

    def __init__(self, *args):
        self.args = args

    def msg(self):
        # Remove None values from args
        args = filter(lambda a: a, self.args)
        return u': '.join((self.name, ) + args)

    __str__ = msg


class PackageError(InstallationError):
    """An error occurring while processing a package.
    """
    name = u'Package error'


class PackageNotFound(PackageError):
    """A package cannot be found.
    """
    name = u'Package not found'


class ConfigurationError(InstallationError):
    """Configuration error.
    """
    name = u'Configuration error'


class FileError(ConfigurationError):
    """Error while accessing a file.
    """
    name = u"File error"


class DownloadError(InstallationError):
    """Error while downloading a file.
    """
    name = u"Download error"
