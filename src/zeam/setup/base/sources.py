
import logging
import re

from zeam.setup.base.distribution import DownloableRelease, Software
from zeam.setup.base.error import ConfigurationError, PackageNotFound
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


class RemoteSource(object):
    """Download software from da internet, in order to install it.
    """

    def __init__(self, config):
        self.config = config
        self.find_links = config['urls'].as_list()
        self.__max_depth = config.get('max_depth', '3').as_int()
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

    def install(self, name, directory):
        raise PackageNotFound(name)

    def __repr__(self):
        return '<Downloader Source for %s>' % str(list(self.find_links))


class LocalSource(object):
    """This represent a directory with a list of archives, that can be
    used to install software.
    """

    def __init__(self, config):
        self.config = config
        self.path = config['directory'].as_text()

    def install(self, name, directory):
        raise PackageNotFound(name)

    def __repr__(self):
        return '<Archive Source at %s>' % self.path


SOURCE_PROVIDERS = {'local': LocalSource,
                    'remote': RemoteSource}


class Source(object):
    """This manage software sources.
    """

    def __init__(self, config, section_name='setup'):
        self.sources = []
        for source_name in config[section_name]['sources'].as_list():
            source_config = config['source:' + source_name]
            type = source_config['type'].as_text()
            if type not in SOURCE_PROVIDERS:
                raise ConfigurationError('Unknow source type %s for %s' % (
                        type, source_name))
            self.sources.append(SOURCE_PROVIDERS[type](source_config))

    def install(self, name, directory):
        """Install the given package name in the directory.
        """
        for source in self.sources:
            try:
                return source.install(name, directory)
            except PackageNotFound:
                continue
        raise PackageNotFound(name)

    def __repr__(self):
        return '<Source %s>' % ', '.join(map(repr, self.sources))
