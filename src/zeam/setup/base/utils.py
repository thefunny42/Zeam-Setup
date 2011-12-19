
import logging
import re
import os
import urllib2
import urlparse
import subprocess

from zeam.setup.base.error import FileError, NetworkError, ConfigurationError

VERSION = re.compile(
    r'version ([0-9.]+)')
HTML_LINK = re.compile(
    r'<a.*?href\s*=\s*["\'](?P<url>[^"\']+)["\'].*?>(?P<name>.+?)?</a>',
    re.IGNORECASE)
STRING_TAGS = re.compile(
    r'<(?P<tag>\S+)(\s.*?)?>.*?</(?P=tag)>|<\S+.*?/>')
logger = logging.getLogger('zeam.setup')


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
                return (True, version.groups()[0])
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
    for protocol in ['http://', 'https://', 'ftp://', 'ftps://']:
        if uri.startswith(protocol):
            return True
    return False

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
            logger.info("Accessing remote url: %s" % uri)
            return urllib2.urlopen(uri)
        except urllib2.URLError, e:
            raise NetworkError(uri)
    try:
        logger.info(u"Reading local file: %s" % uri)
        return open(uri, 'r')
    except IOError, e:
        raise FileError(uri, e.args[1])


def rewrite_links(base_uri, links, lower=False):
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
        if not name:
            # If we have no name, we use the last part of the URL.
            link_parts = urlparse.urlparse(url)
            name = os.path.basename(link_parts[2])
        else:
            name = STRING_TAGS.sub('', name)
        key = name.strip()
        if lower:
            key = key.lower()
        yield (key, url)


def get_links(uri, lower=False):
    """Read all available links from a page.
    """
    http_stream = open_uri(uri)
    try:
        content_type = http_stream.headers.get('content-type', '').split(';')[0]
        if content_type not in ['text/html']:
            return {}
        html = http_stream.read()
        return dict(rewrite_links(uri, HTML_LINK.findall(html), lower=lower))
    finally:
        http_stream.close()

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

