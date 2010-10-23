

import logging
import os
import re

from zeam.setup.base.distribution.collection import ReleaseSet
from zeam.setup.base.distribution.egg import EggRelease
from zeam.setup.base.distribution.sources import (
    UninstalledRelease, UndownloadedRelease)
from zeam.setup.base.download import DownloadManager
from zeam.setup.base.error import ConfigurationError, PackageNotFound
from zeam.setup.base.utils import get_links, create_directory
from zeam.setup.base.vcs import VCS

logger = logging.getLogger('zeam.setup')

RELEASE_TARBALL = re.compile(
    r'^(?P<name>[^-]+)-(?P<version>[^-]*(-[\d]+)?)'
    r'(-py(?P<pyversion>[^-]+)(-(?P<platform>[\w]+))?)?'
    r'\.(?P<format>zip|egg|tgz|tar\.gz)$',
    re.IGNORECASE)


def get_release_from_name(source, name, url=None):
    """Return a not installed release from the given name.
    """
    info = RELEASE_TARBALL.match(name)
    if info:
        name = info.group('name')
        version = info.group('version')
        format = info.group('format')
        pyversion = info.group('pyversion')
        platform = info.group('platform')
        return source.factory(
            source, name, version, format, url, pyversion, platform)
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
        full_filename = os.path.join(directory, filename)
        if not os.path.isfile(full_filename):
            continue
        release = get_release_from_name(source, filename, full_filename)
        if release is not None:
            yield release

def get_eggs_from_directory(source, directory):
    """Get a list of egg releases from a directory
    """
    for filename in os.listdir(directory):
        full_filename = os.path.join(directory, filename)
        if not os.path.isdir(full_filename):
            continue
        info = RELEASE_TARBALL.match(full_filename)
        if info:
            yield source.factory(full_filename)



class RemoteSource(object):
    """Download software from da internet, in order to install it.
    """
    factory = UndownloadedRelease

    def __init__(self, options):
        self.options = options
        self.find_links = options['urls'].as_list()
        self.max_depth = options.get('max_depth', '3').as_int()
        self.links = {}
        self.software = ReleaseSet()
        self.downloader = DownloadManager(self.get_download_directory())

    def get_download_directory(self):
        """Return the created download directory.
        """
        directory = self.options['download_directory'].as_text()
        create_directory(directory)
        return directory

    def get_download_packages(
        self, requirement, find_link, interpretor, depth=0):
        if depth > self.max_depth:
            return None

        pyversion = interpretor.get_pyversion()
        platform = interpretor.get_platform()
        if find_link not in self.links:
            links = get_links(find_link)
            self.links[find_link] = links
            # Add found software in the cache
            self.software.extend(get_releases_from_links(self, links))

        # Look for a software in the cache
        releases = self.software.get_releases_for(
            requirement, pyversion, platform)
        if releases:
            return releases

        # No software, look for an another link with the name of the software
        links = self.links[find_link]
        if requirement.name in links:
            return self.get_download_packages(
                requirement, links[requirement.name], interpretor, depth + 1)
        return None

    def initialize(self):
        pass

    def available(self, configuration):
        setup_config = configuration['setup']
        offline = 'offline' in setup_config and \
            setup_config['offline'].as_bool()
        return not offline

    def search(self, requirement, interpretor):
        for find_link in self.find_links:
            __status__ = u"Locating remote source for %s on %s" % (
                requirement, find_link)
            packages = self.get_download_packages(
                requirement, find_link, interpretor)
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
    type = 'Archive Source'
    finder = get_releases_from_directory

    def __init__(self, options):
        __status__ = u"Initializing local software sourcs."
        self.options = options
        self.path = options['directory'].as_text()
        self.software = ReleaseSet()

    def initialize(self):
        __status__ = u"Analysing local software source %s." % self.path
        create_directory(self.path)
        self.software.extend(self.finder(self.path))

    def available(self, configuration):
        return True

    def search(self, requirement, interpretor):
        __status__ = u"Locating local source for %s in %s." % (
            requirement, self.path)
        pyversion = interpretor.get_pyversion()
        platform = interpretor.get_platform()
        packages = self.software.get_releases_for(
            requirement, pyversion, platform)
        if packages:
            return packages
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<%s at %s>' % (self.type, self.path)


class EggsSource(LocalSource):
    """This manage installed sources.
    """
    factory = EggRelease
    type = 'Eggs'
    finder = get_eggs_from_directory


class VCSSource(object):
    """This sources fetch the code from various popular version
    control system.
    """

    def __init__(self, options):
        __status__ = u"Initializing remote development sources."
        self.options = options
        self.directory = options['directory'].as_text()
        self.sources = {}
        self.enabled = options['available'].as_list()

    def initialize(self):
        __status__ = u"Preparing remote development sources."
        for section_name in self.options['sources'].as_list():
            section = self.options.configuration['vcs:' + section_name]
            for package_name, source_info in section.items():
                parsed_source_info = source_info.as_words()
                if len(parsed_source_info) < 2:
                    raise ConfigurationError(
                        source_info.location,
                        u"Malformed source description for package %s" % (
                            package_name))
                uri = parsed_source_info[1]
                vcs = VCS.get(parsed_source_info[0], package_name, source_info)
                directory = os.path.join(self.directory, package_name)
                self.sources[package_name] = vcs(uri, directory)

    def available(self, configuration):
        # This source provider is always available
        return True

    def search(self, requirement, interpretor):
        name = requirement.name
        if name in self.enabled:
            if name not in self.sources:
                raise ConfigurationError(
                    u"Package %s is marked as available with a VCS source, "
                    u"but no VCS source is configured for it" % name)
            source = self.sources[name]
            source.install()
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<VCSSource at %s>' % (self.type, self.path)


SOURCE_PROVIDERS = {'local': LocalSource,
                    'remote': RemoteSource,
                    'eggs': EggsSource,
                    'vcs': VCSSource}

class Sources(object):
    """This manage software sources.
    """

    def __init__(self, configuration, section_name='setup'):
        __status__ = u"Initializing software sources."
        self.sources = []
        self.configuration = configuration
        for source_name in configuration[section_name]['sources'].as_list():
            source_config = configuration['source:' + source_name]
            type = source_config['type'].as_text()
            if type not in SOURCE_PROVIDERS:
                raise ConfigurationError(
                    u'Unknow source type %s for %s' % (
                        type, source_name))
            self.sources.append(SOURCE_PROVIDERS[type](source_config))
        self.__initialized = False

    def initialize(self):
        if self.__initialized:
            return
        for source in self.sources:
            source.initialize()
        self.__initialized = True

    def search(self, requirement, interpretor):
        """Search of a given package at the given location.
        """
        for source in self.sources:
            if not source.available(self.configuration):
                continue
            try:
                return source.search(requirement, interpretor)
            except PackageNotFound:
                continue
        raise PackageNotFound(repr(requirement))

    def __repr__(self):
        return '<Source %s>' % ', '.join(map(repr, self.sources))

