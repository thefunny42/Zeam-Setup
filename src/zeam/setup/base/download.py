
import logging
import re

from zeam.setup.base.distribution import DownloableRelease, Software
from zeam.setup.base.utils import get_links

logger = logging.getLogger('zeam.setup')

RELEASE_TARBALL = re.compile(
    r'^(?P<name>[^-]+)-(?P<version>.*)'
    r'(-py(?P<pyversion>[^-])(-(?P<platform>[\w]+))?)?'
    r'\.(?P<format>zip|egg|tgz|tar\.gz)$',
    re.IGNORECASE)


def get_releases_from_links(links):
    """Get downloadable software from links.
    """

    for name, url in links.iteritems():
        info = RELEASE_TARBALL.match(name)
        if info:
            name = info.group('name').lower()
            yield DownloableRelease(name,
                                    info.group('version'),
                                    info.group('format'),
                                    url)


class Downloader(object):
    """Download software from da internet.
    """

    def __init__(self, find_links, max_depth=3):
        self.find_links = find_links
        self.__max_depth = max_depth
        self.__links_cache = {}
        self.__software_cache = {}

    def __download(self, name, find_link, depth=0):
        if depth > self.__max_depth:
            return None

        if find_link not in self.__links_cache:
            links = get_links(find_link)
            self.__links_cache[find_link] = links
            # Add found software in the cache
            for release in get_releases_from_links(links):
                cache = self.__software_cache.setdefault(
                    release.name, Software(release.name))
                cache.add(release)

        # Look for a software in the cache
        if name in self.__software_cache:
            return self.__software_cache[name]

        # No software, look for an another link with the name of the software
        links = self.__links_cache[find_link]
        if name in links:
            return self.__download(name, links[name], depth + 1)
        return None

    def download(self, name, version=None):
        name = name.lower()
        for find_link in self.find_links:
            stuff = self.__download(name, find_link, version=version)

    def __repr__(self):
        return '<Downloader for %s>' % str(list(self.find_links))


class ArchiveDirectory(object):

    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return '<Archive Directory at %s>' % self.path

