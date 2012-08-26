
import logging
import os
import re
import subprocess
import urllib2

from monteur.error import FileError, NetworkError, ConfigurationError

VERSION = re.compile(r'(version)? ([0-9\.]+)')
logger = logging.getLogger('monteur')


def have_cmd(*cmd):
    """Test if a command is available.
    """
    try:
        logger.info('Testing command: %s', ' '.join(cmd))
        process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        for line in stdout.splitlines():
            version = VERSION.search(line)
            if version:
                return (True, version.groups()[-1])
    except OSError, error:
        if error.args[0] == 2:
            return (False, None)
    return (True, None)


def get_cmd_output(*cmd, **opts):
    """Run an external command and return its result (output, error
    output, return code).
    """
    path = opts.get('path', None)
    environ = opts.get('environ', None)
    cmd_environ = None
    debug_cmd = []
    debug_postfix = []
    if path:
        debug_postfix.append('in %s' % (path))
    if environ:
        debug_cmd.append(' '.join(map('='.join, environ.items())))
        cmd_environ = os.environ.copy()
        cmd_environ.update(environ)
    debug_cmd.extend(cmd)
    debug_msg = 'Running command: %s' % ' '.join(debug_cmd)
    if debug_postfix:
        debug_msg += ' [' + ' '.join(debug_postfix) + ']'
    logger.debug(debug_msg)
    stdout = subprocess.PIPE
    stderr = subprocess.PIPE
    if opts.get('no_stdout'):
        stdout = None
        stderr = None
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
        cwd=path, env=cmd_environ)
    stdout, stderr = process.communicate(input=opts.get('input', None))
    return stdout, stderr, process.returncode

def is_remote_uri(uri):
    """Tell you if the given uri is remote.
    """
    # XXX Todo check for SSL availability
    for protocol in ['http://', 'https://', 'ftp://', 'ftps://']:
        if uri.startswith(protocol):
            return True
    return False

def absolute_uri(uri):
    """Return an absolute URI for the given path.
    """
    if not is_remote_uri(uri) and not os.path.isabs(uri):
        return os.path.abspath(uri)
    return uri

def relative_uri(origin, target, is_container=False):
    """Return an URI for target, paying attention that if it was
    relative, it was from origin.
    """
    if target.startswith(os.path.sep) or is_remote_uri(target):
        return target
    if origin:
        origin = origin.split(os.path.sep)
        if not is_container:
            origin = origin[:-1]
        return os.path.sep.join(origin + [target])
    return target

def open_uri(uri):
    """Open the given file or uri.
    """
    if is_remote_uri(uri):
        # XXX Todo add a caching subsystem
        try:
            logger.info("Accessing remote url: %s", uri)
            return urllib2.urlopen(uri)
        except urllib2.URLError, e:
            raise NetworkError(uri)
    try:
        logger.info(u"Reading local file: %s", uri)
        return open(uri, 'r')
    except IOError, e:
        raise FileError(uri, e.args[1])

def compare_uri(uri1, uri2):
    """Compare two URIs together, discarding the last '/'.
    """
    return uri1.rstrip('/') == uri2.rstrip('/')

def create_directory(directory, quiet=False):
    """Create a directory called directory if it doesn't exits
    already.
    """
    directory = directory.strip()
    if not os.path.isdir(directory):
        if not quiet:
            logger.info('Creating directory %s', directory)
        os.makedirs(directory)
    return directory

# Configuration related helpers

def get_package_name(section):
    """Return the package name option used in the section or the
    default one of the configuration.
    """
    if 'package' in section:
        return section['package']
    configuration = section.configuration
    if 'egginfo' in configuration:
        return configuration['egginfo']['name']
    raise ConfigurationError('Cannot determine package name')


def format_line(start_line, end_line=None):
    """Format location information to report it.
    """
    location = u'line %d' % (start_line)
    if end_line is not None and end_line != start_line:
        location += u' to %d' % end_line
    return location
