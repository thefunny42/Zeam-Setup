
import logging
import re
import os
import urllib2
import urlparse
import subprocess

from zeam.setup.base.error import FileError, NetworkError, ConfigurationError

HTML_LINK = re.compile(
    r'<[aA][^>]*[hH][rR][eE][fF]=["\'](?P<url>[^"\']+)["\'][^>]*>'
    r'(?P<name>[^<]+)</[aA\s]>')

logger = logging.getLogger('zeam.setup')


def have_cmd(*cmd):
    """Test if a command is available.
    """
    try:
        logger.debug('Testing command: %s', ' '.join(cmd))
        process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        process.communicate()
    except OSError, error:
        if error.args[0] == 2:
            return False
    return True


def get_cmd_output(*cmd, **opts):
    """Run an external command and return its result (output, error
    output, return code).
    """
    path = opts.get('path', None)
    environ = opts.get('environ', None)
    debug_msg = 'Running command: %s' % ' '.join(cmd)
    debug_extra = []
    if path:
        debug_extra.append('in %s' % (path))
    if environ:
        debug_extra.append(' '.join(map('='.join, environ.items())))
    if debug_extra:
        debug_msg += ' [' + ' '.join(debug_extra) + ']'
    logger.debug(debug_msg)
    stdout = subprocess.PIPE
    stderr = subprocess.PIPE
    if opts.get('no_stdout'):
        stdout = None
        stderr = None
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
        cwd=path, env=environ)
    stdout, stderr = process.communicate()
    return stdout, stderr, process.returncode


def is_remote_uri(uri):
    """Tell you if the given uri is remote.
    """
    # XXX Todo check for SSL availability
    return uri.startswith('http://') or uri.startswith('https://')


def open_uri(uri):
    """Open the given file or uri.
    """
    if is_remote_uri(uri):
        # XXX Todo add a caching subsystem
        try:
            logger.info("Accessing remote url %s" % uri)
            return urllib2.urlopen(uri)
        except urllib2.URLError, e:
            raise NetworkError(uri, e.args[0].args[1])
    try:
        logger.info(u"Reading local file %s" % uri)
        return open(uri, 'r')
    except IOError, e:
        raise FileError(uri, e.args[1])


def rewrite_links(base_uri, links):
    """This rewrite a list of links as full uri, using base_uri as
    source.
    """
    uri_parts = urlparse.urlparse(base_uri)
    absolute_uri = uri_parts[0:2]
    relative_path = uri_parts[2]
    if not relative_path.endswith('/'):
        relative_path = os.path.dirname(relative_path)
    elif not relative_path:
        relative_path = '/'

    for url, name in links:
        if url:
            if url[0] == '/':
                # Convert absolute URL to absolute URI
                url = urlparse.urlunparse(absolute_uri + (url, '', '', '',))
            elif not is_remote_uri(url):
                url = urlparse.urlunparse(absolute_uri + (
                        os.path.join(relative_path, url), '','', ''))
        yield (name.strip(), url,)


def get_links(uri):
    """Read all available links from a page.
    """

    input = open_uri(uri)
    html = input.read()
    input.close()

    return dict(rewrite_links(uri, HTML_LINK.findall(html)))


def create_directory(directory):
    """Create a directory called directory if it doesn't exits
    already.
    """
    directory = directory.strip()
    if not os.path.isdir(directory):
        logger.info('Creating directory %s' % directory)
        os.makedirs(directory)

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


def get_option_with_default(option_name, section, required=True):
    """Lookup a option in a given section, and if nothing is found,
    lookup the value in the [setup] section.
    """
    if option_name in section:
        return section[option_name]
    setup = section.configuration['setup']
    if option_name in setup:
        return setup[option_name]
    if required:
        raise ConfigurationError('Cannot find %s value' % option_name)
    return None
