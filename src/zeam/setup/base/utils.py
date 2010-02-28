
import logging
import re
import os
import urllib2
import urlparse

from zeam.setup.base.error import FileError, ConfigurationError

HTML_LINK = re.compile(
    r'<[aA][^>]*[hH][rR][eE][fF]=["\'](?P<url>[^"\']+)["\'][^>]*>'
    r'(?P<name>[^<]+)</[aA\s]>')

logger = logging.getLogger('zeam.setup')


def open_uri(uri):
    """Open the given file or uri.
    """
    # XXX Todo check for SSL availability
    if uri.startswith('http://') or uri.startswith('https://'):
        # XXX Todo add a caching subsystem
        try:
            logger.info("Accessing remote url %s" % uri)
            return urllib2.urlopen(uri)
        except urllib2.URLError, e:
            raise FileError(uri, e.msg)
    try:
        return open(uri, 'r')
    except IOError, e:
        raise FileError(uri, e.args[1])


def get_links(uri):
    """Read all available links from a page.
    """
    links = []
    uri_parts = urlparse.urlparse(uri)[0:2]

    input = open_uri(uri)
    html = input.read()
    input.close()

    for url, name in HTML_LINK.findall(html):
        if url and url[0] == '/':
            # Convert relative URLs to absolute ones
            url = urlparse.urlunparse(uri_parts + (url, '', '', '',))
        links.append((name.strip().lower(), url,))
    return dict(links)


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


def get_option_with_default(option_name, section):
    """Lookup a option in a given section, and if nothing is found,
    lookup the value in the [setup] section.
    """
    if option_name in section:
        return section[option_name]
    setup = section.configuration['setup']
    if option_name in setup:
        return setup[option_name]
    raise ConfigurationError('Cannot find %s value' % option_name)
