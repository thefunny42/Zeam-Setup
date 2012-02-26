
import logging
import pdb
import sys
import thread
import threading
import traceback
import os
from datetime import datetime
from cStringIO import StringIO

logger = logging.getLogger('zeam.setup')

VERBOSE_LVL_TO_LOGGING_LVL = {0: logging.ERROR,
                              1: logging.WARNING,
                              2: logging.INFO,
                              3: logging.DEBUG}
VERBOSE_LVL = lambda lvl: VERBOSE_LVL_TO_LOGGING_LVL.get(lvl, logging.DEBUG)


class NamedFormatter(logging.Formatter):

    def __init__(self, get_name, fmt=None):
        logging.Formatter.__init__(self, fmt=fmt)
        self._get_name = get_name

    def format(self, record):
        message = logging.Formatter.format(self, record)
        return '[%s] %s' % (self._get_name(), message)


class LoggerUtility(object):
    filename = 'error.log'

    def __init__(self):
        self._lock = threading.Lock()
        self._append_to_file = False
        self._debug = False
        self._names = {thread.get_ident(): os.path.basename(sys.argv[0])}
        self._logs = StringIO()
        for stream in [sys.stdout, self._logs]:
            handler = logging.StreamHandler(stream)
            handler.setFormatter(NamedFormatter(self._get_name, '%(message)s'))
            logger.addHandler(handler)

    def configure(self, level, debug=False):
        logger.setLevel(VERBOSE_LVL(level))
        self._debug = debug

    def register(self, name):
        self._names[thread.get_ident()] = name

    def unregister(self):
        ident = thread.get_ident()
        if ident in self._names:
            del self._names[ident]

    def _get_name(self):
        return self._names.get(thread.get_ident(), u'unknown')

    def _open_error_file(self):
        # Return a file suitable to log errors.
        try:
            error_file =open(self.filename, self._append_to_file and 'a' or 'w')
            self._append_to_file = True
            return error_file
        except IOError:
            return None

    def _create_report(self, cls, error, trace):
        """Log last error in a file.
        """
        error_file = self._open_error_file()
        if error_file is not None:
            error_file.write(u'==== %s in %s ====\n' % (
                    datetime.now(), self._get_name()))
            error_file.write(u'%s: %s:\n' % (cls.__name__, error))
            traceback.print_tb(trace, None, error_file)
            error_file.close()

    def report(self, fatal=True, configuration=None):
        """Display the last error, and quit.
        """
        self._lock.acquire()
        try:
            logger.critical(u'')
            logger.critical(u'An error happened:')
            exc_info = sys.exc_info()
            cls, error, trace = exc_info
            while trace is not None:
                locals = trace.tb_frame.f_locals
                if '__status__' in locals:
                    logger.critical(u'While: %s' % locals['__status__'])
                trace = trace.tb_next

            cls, error, trace = exc_info
            if not self._debug:
                self._create_report(cls, error, trace)

            if self._debug:
                logger.critical(u'\nDebuging error:')
                logger.critical(u'\n%s: %s:' % (cls.__name__, error))
                pdb.post_mortem(trace)
                if fatal:
                    sys.exit(0)
            else:
                if issubclass(cls, InstallationError):
                    logger.critical(error.msg())
                    for line in error.extra():
                        logger.info(line)
                else:
                    logger.critical(u'')
                    logger.critical(
                        u'Unexpected error. '
                        u'Please contact vendor with error.log')
                if fatal:
                    error_file = self._open_error_file()
                    if error_file is not None:
                        if configuration is not None:
                            try:
                                error_file.write('\n==== configuration ====\n')
                                configuration.write(error_file)
                            except:
                                pass
                        error_file.write('\n==== log ====\n')
                        error_file.write(self._logs.getvalue())
                    sys.exit(-1)
        finally:
            self._lock.release()

# Expose API.
logs = LoggerUtility()


class InstallationError(Exception):
    """Installation happening while installation.
    """
    name = u'Installation error'

    def __init__(self, *args, **kwargs):
        self.args = args
        self.detail = kwargs.get('detail', None)
        self.command = kwargs.get('command', None)

    def msg(self):
        # Remove None values from args
        args = filter(lambda a: a, self.args)
        return u': '.join((self.name, ) + args)

    def extra(self):
        if self.command:
            yield '$ ' + ' '.join(self.command)
        if self.detail:
            for line in self.detail.splitlines():
                yield line

    __str__ = msg


class PackageError(InstallationError):
    """An error occurring while processing a package.
    """
    name = u'Package error'


class PackageNotFound(PackageError):
    """A package cannot be found.
    """
    name = u'Package not found'


class PackageDistributionError(PackageError):
    """A distribution of a package cannot be installed. An another
    distribution should work.
    """
    name = u'Distribution error'


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
