
import urllib2
import urlparse
import re

from zeam.setup.base.error import FileError

HTML_LINK = re.compile(
    r'<[aA][^>]*[hH][rR][eE][fF]=["\'](?P<url>[^"\']+)["\'][^>]*>'
    r'(?P<name>[^<]+)</[aA\s]>')


def open_uri(uri):
    """Open the given file or uri.
    """
    # XXX Todo check for SSL availability
    if uri.startswith('http://') or uri.startswith('https://'):
        # XXX Todo add a caching subsystem
        try:
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
