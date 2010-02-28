
import logging
import re

from zeam.setup.base.distribution import UninstalledRelease, Software
from zeam.setup.base.error import ConfigurationError, PackageNotFound
from zeam.setup.base.utils import get_links, create_directory

logger = logging.getLogger('zeam.setup')

RELEASE_TARBALL = re.compile(
    r'^(?P<name>[^-]+)-(?P<version>.*)'
    r'(-py(?P<pyversion>[^-])(-(?P<platform>[\w]+))?)?'
    r'\.(?P<format>zip|egg|tgz|tar\.gz)$',
    re.IGNORECASE)


def get_release_from_name(name, url=None):
    """Return a not installed release from the given name.
    """
    info = RELEASE_TARBALL.match(name)
    if info:
        name = info.group('name').lower()
        version = info.group('version')
        format = info.group('format')
        return UninstalledRelease(name, version, format, url)
    return None


def get_releases_from_links(links):
    """Get downloadable software from links.
    """
    for name, url in links.iteritems():
        release = get_release_from_name(name, url)
        if release is not None:
            yield release

def get_releases_from_directory(directory):
    """Get a list of release from a directory.
    """
    for filename in os.listdir(directory):
        if not os.path.isfile(filename):
            continue
        release = get_release_from_name(name, os.path.join(directory, name))
        if release is not None:
            yield release


class AvailableSoftware(object):
    """Represent the available software.
    """

    def __init__(self):
        self.software = {}

    def add(self, release):
        """Add a software to the available ones.
        """
        software = self.software.setdefault(
            release.name, Software(release.name))
        software.add(release)

    def extend(self, releases):
        """Extend the available software by adding a list of releases to it.
        """
        for release in releases:
            self.add(release)

    def __getitem__(self, name):
        return self.software[name]

    def __contains__(self, name):
        return name in self.software


class RemoteSource(object):
    """Download software from da internet, in order to install it.
    """

    def __init__(self, config):
        self.config = config
        self.find_links = config['urls'].as_list()
        self.max_depth = config.get('max_depth', '3').as_int()
        self.links = {}
        self.software = AvailableSoftware()

    def __download(self, name, find_link, depth=0):
        if depth > self.max_depth:
            return None

        if find_link not in self.links:
            links = get_links(find_link)
            self.links[find_link] = links
            # Add found software in the cache
            self.software.extend(get_releases_from_links(links))

        # Look for a software in the cache
        if name in self.software:
            return self.software[name]

        # No software, look for an another link with the name of the software
        links = self.links[find_link]
        if name in links:
            return self.download(name, links[name], depth + 1)
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
        self.software = AvailableSoftware()
        self.__loaded = True

    def load(self):
        """Internally load available archives in the directory.
        """
        if self.__loaded:
            return
        create_directory(self.path)
        self.software.extend(get_releases_from_directory(self.path))
        self.__loaded = True

    def install(self, name, directory):
        self.load()
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
