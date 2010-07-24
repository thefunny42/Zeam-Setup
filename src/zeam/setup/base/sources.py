
import logging
import os
import re

from zeam.setup.base.distribution import Software
from zeam.setup.base.distribution.egg import EggRelease
from zeam.setup.base.distribution.sources import (
    UninstalledRelease, UndownloadedRelease)
from zeam.setup.base.download import DownloadManager
from zeam.setup.base.error import ConfigurationError, PackageNotFound
from zeam.setup.base.utils import get_links, create_directory
from zeam.setup.base.version import Requirement

logger = logging.getLogger('zeam.setup')

RELEASE_TARBALL = re.compile(
    r'^(?P<name>[^-]+)-(?P<version>[^-]*)'
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

    def get_releases_for(self, requirement, pyversion=None, platform=None):
        if not requirement.name in self.software:
            return []
        return self.software[requirement.name].get_releases_for(
            requirement, pyversion=pyversion, platform=platform)


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

    def available(self, config):
        setup_config = config['setup']
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

    def __init__(self, config):
        self.config = config
        self.path = config['directory'].as_text()
        self.software = AvailableSoftware()
        self.__loaded = False

    def load(self):
        """Internally load available archives in the directory.
        """
        if self.__loaded:
            return
        create_directory(self.path)
        self.software.extend(self.finder(self.path))
        self.__loaded = True

    def available(self, config):
        return True

    def search(self, requirement, interpretor):
        __status__ = u"Locating local source for %s in %s" % (
            requirement, self.path)
        self.load()
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


SOURCE_PROVIDERS = {'local': LocalSource,
                    'remote': RemoteSource,
                    'eggs': EggsSource,}

class Source(object):
    """This manage software sources.
    """

    def __init__(self, config, section_name='setup'):
        self.sources = []
        self.config = config
        for source_name in config[section_name]['sources'].as_list():
            source_config = config['source:' + source_name]
            type = source_config['type'].as_text()
            if type not in SOURCE_PROVIDERS:
                raise ConfigurationError('Unknow source type %s for %s' % (
                        type, source_name))
            self.sources.append(SOURCE_PROVIDERS[type](source_config))

    def search(self, requirement, interpretor):
        """Search of a given package at the given location.
        """
        for source in self.sources:
            if not source.available(self.config):
                continue
            try:
                return source.search(requirement, interpretor)
            except PackageNotFound:
                continue
        raise PackageNotFound(repr(requirement))

    def __repr__(self):
        return '<Source %s>' % ', '.join(map(repr, self.sources))


class PackageInstaller(object):
    """Install new packages.
    """

    def __init__(self, environment, source, target_directory):
        self.environment = environment
        self.source = source
        self.target_directory = os.path.abspath(target_directory)
        self.newly_installed = dict()

    def install(self, requirement):
        """Install the given package name in the directory.
        """
        if requirement in self.newly_installed:
            return self.newly_installed[requirement]
        candidate_packages = self.source.search(
            requirement, self.environment.default_interpretor)
        logger.debug(u"Package versions found for %s: %s." % (
                requirement.name,
                ', '.join(map(lambda p: str(p.version),
                              candidate_packages.releases))))
        source_package = candidate_packages.get_most_recent_release()
        logger.info(u"Picking version %s for %s." % (
                str(source_package.version), requirement.name))
        installed_package = source_package.install(
            self.target_directory,
            self.environment.default_interpretor,
            self.install)
        self.newly_installed[requirement] = installed_package
        if installed_package:
            self.environment.add(installed_package)
        return installed_package

