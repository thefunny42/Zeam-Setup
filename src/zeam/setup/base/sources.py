
import logging
import os
import re

from zeam.setup.base.distribution import Software
from zeam.setup.base.distribution.sources import (
    UninstalledRelease, UndownloadedRelease)
from zeam.setup.base.download import DownloadManager
from zeam.setup.base.error import ConfigurationError, PackageNotFound
from zeam.setup.base.utils import get_links, create_directory
from zeam.setup.base.version import Requirement

logger = logging.getLogger('zeam.setup')

RELEASE_TARBALL = re.compile(
    r'^(?P<name>[^-]+)-(?P<version>.*)'
    r'(-py(?P<pyversion>[^-])(-(?P<platform>[\w]+))?)?'
    r'\.(?P<format>zip|egg|tgz|tar\.gz)$',
    re.IGNORECASE)


def get_release_from_name(source, name, url=None):
    """Return a not installed release from the given name.
    """
    info = RELEASE_TARBALL.match(name)
    if info:
        name = info.group('name').lower()
        version = info.group('version')
        format = info.group('format')
        return source.factory(source, name, version, format, url)
    return None


def get_releases_from_links(source, links):
    """Get downloadable software from links.
    """
    for name, url in links.iteritems():
        release = get_release_from_name(source, name, url)
        if release is not None:
            yield release

def get_releases_from_directory(source, directory):
    """Get a list of release from a directory.
    """
    for filename in os.listdir(directory):
        if not os.path.isfile(filename):
            continue
        release = get_release_from_name(
            source, filename, os.path.join(directory, filename))
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

    def __getitem__(self, key):
        if isinstance(key, Requirement):
            return self.software[key.name][key]
        return self.software[key]

    def __contains__(self, requirement):
        try:
            return len(self[requirement]) != 0
        except KeyError:
            return False


class RemoteSource(object):
    """Download software from da internet, in order to install it.
    """
    factory = UndownloadedRelease

    def __init__(self, config):
        self.config = config
        self.find_links = config['urls'].as_list()
        self.max_depth = config.get('max_depth', '3').as_int()
        self.links = {}
        self.software = AvailableSoftware()
        self.downloader = DownloadManager(self.get_download_directory())

    def get_download_directory(self):
        """Return the created download directory.
        """
        directory = self.config['download_directory'].as_text()
        create_directory(directory)
        return directory

    def get_download_packages(self, requirement, find_link, depth=0):
        if depth > self.max_depth:
            return None

        if find_link not in self.links:
            links = get_links(find_link)
            self.links[find_link] = links
            # Add found software in the cache
            self.software.extend(get_releases_from_links(self, links))

        # Look for a software in the cache
        if requirement in self.software:
            return self.software[requirement]

        # No software, look for an another link with the name of the software
        links = self.links[find_link]
        if requirement.name in links:
            return self.get_download_packages(
                requirement, links[requirement.name], depth + 1)
        return None

    def search(self, requirement):
        for find_link in self.find_links:
            __status__ = u"Locating remote source for %s on %s" % (
                requirement, find_link)
            packages = self.get_download_packages(requirement, find_link)
            if packages is not None:
                return packages
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<Downloader Source for %s>' % str(list(self.find_links))


class LocalSource(object):
    """This represent a directory with a list of archives, that can be
    used to install software.
    """
    factory = UninstalledRelease

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

    def search(self, requirement):
        __status__ = u"Locating local source for %s in %s" % (
            requirement, self.path)
        self.load()
        raise PackageNotFound(requirement)

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

    def install(self, requirement, directory):
        """Install the given package name in the directory.
        """
        packages = self.search(requirement)
        logger.debug(u"Package versions found for %s: %s." % (
                requirement.name,
                ', '.join(map(lambda p: str(p.version), packages.releases))))
        package = packages.get_most_recent()
        logger.info(u"Picking version %s for %s." % (
                str(package.version), requirement.name))
        return package.install(directory)


    def search(self, requirement):
        """Search of a given package at the given location.
        """
        for source in self.sources:
            try:
                return source.search(requirement)
            except PackageNotFound:
                continue
        raise PackageNotFound(repr(requirement))

    def __repr__(self):
        return '<Source %s>' % ', '.join(map(repr, self.sources))
