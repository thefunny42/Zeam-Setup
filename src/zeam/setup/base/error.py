
import logging
import pdb
import sys
import threading
import traceback

logger = logging.getLogger('zeam.setup')

__reporting_lock = threading.Lock()

def create_report(type, error, trace, filename='error.log'):
    """Log last error in a file.
    """
    try:
        error_file = open(filename, 'w')
        error_file.write(u'%s: %s:\n' % (type.__name__, error))
        traceback.print_tb(trace, None, error_file)
        error_file.close()
    except IOError:
        pass


def report_error(debug=False, fatal=True):
    """Display the last error, and quit.
    """
    try:
        __reporting_lock.acquire()
        logger.critical(u'\nAn error happened:')
        exc_info = sys.exc_info()
        type, error, trace = exc_info
        while trace is not None:
            locals = trace.tb_frame.f_locals
            if '__status__' in locals:
                logger.critical(u'While: %s' % locals['__status__'])
            trace = trace.tb_next

        type, error, trace = exc_info
        if not debug:
            create_report(type, error, trace)

        if debug:
            logger.critical(u'\nDebuging error:')
            logger.critical(u'\n%s: %s:' % (type.__name__, error))
            pdb.post_mortem(trace)
            if fatal:
                sys.exit(0)
        else:
            if issubclass(type, InstallationError):
                logger.critical(error.msg())
            else:
                logger.critical(
                    u'\nUnexpected error. Please contact vendor with error.log')
            if fatal:
                sys.exit(-1)
    finally:
        __reporting_lock.release()


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


class NetworkError(FileError):
    """Error while accessing a file over the network.
    """
    name = u"Network error"


class DownloadError(InstallationError):
    """Error while downloading a file.
    """
    name = u"Download error"
