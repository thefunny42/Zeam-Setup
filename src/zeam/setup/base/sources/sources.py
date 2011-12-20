
import logging
import os
import re
import threading

from zeam.setup.base.sources.collection import Installers
from zeam.setup.base.sources.installers import (
    UndownloadedPackageInstaller,
    ExtractedPackageInstaller,
    UninstalledPackageInstaller,
    FakeInstaller,
    PackageInstaller)
from zeam.setup.base.download import DownloadManager
from zeam.setup.base.error import ConfigurationError, PackageNotFound
from zeam.setup.base.error import NetworkError
from zeam.setup.base.utils import get_links, create_directory
from zeam.setup.base.version import Version, InvalidVersion
from zeam.setup.base.version import Requirements
from zeam.setup.base.vcs import VCS, VCSCheckout

logger = logging.getLogger('zeam.setup')

RELEASE_TARBALL = re.compile(
    r'^(?P<name>.*?)-(?P<version>[^-]*(-[\d]+)?(-[\w]+)*(-r[\d]+)?)'
    r'(-py(?P<pyversion>[\d.]+)(-(?P<platform>[\w\d_.-]+))?)?'
    r'\.(?P<format>zip|egg|tgz|tar\.gz)$',
    re.IGNORECASE)
DOWNLOAD_URL = re.compile(r'.*download.*', re.IGNORECASE)


def get_installer_from_name(source, link, url=None, path=None):
    """Return a not installed installer from the given name.
    """
    info = RELEASE_TARBALL.match(link)
    if info:
        try:
            name = info.group('name')
            version = Version.parse(info.group('version'))
            format = info.group('format')
            pyversion = info.group('pyversion')
            platform = info.group('platform')
            return source.factory(
                source,
                name=name, version=version, format=format, url=url, path=path,
                pyversion=pyversion, platform=platform)
        except InvalidVersion:
            logger.debug("Can't process '%s', ignoring it." % link)
            return None
    return None


def get_installers_from_links(source, links):
    """Get downloadable software from links.
    """
    for name, url in links.iteritems():
        installer = get_installer_from_name(source, name, url=url)
        if installer is not None:
            yield installer

def get_installers_from_directory(source, path):
    """Get a list of installer from a directory.
    """
    for filename in os.listdir(path):
        full_path = os.path.join(path, filename)
        if not os.path.isfile(full_path):
            continue
        installer = get_installer_from_name(source, filename, url=full_path)
        if installer is not None:
            yield installer

def get_eggs_from_directory(source, path):
    """Get a list of egg installers from a directory
    """
    for filename in os.listdir(path):
        full_path = os.path.join(path, filename)
        if not os.path.isdir(full_path):
            continue
        installer = get_installer_from_name(source, filename, path=full_path)
        if installer is not None:
            yield installer


class RemoteSearchQuery(object):
    """Bind a search for a requirement.
    """

    def __init__(self, requirement, interpretor, cache):
        self.name = requirement.name
        self.key = requirement.name.lower()
        self.requirement = requirement
        self.cache = cache
        self.pyversion = interpretor.get_pyversion()
        self.platform = interpretor.get_platform()

    def query(self):
        return self.cache.get_installers_for(
            self.requirement, self.pyversion, self.platform)


class RemoteSource(object):
    """Download software from da internet, in order to install it.
    """
    factory = UndownloadedPackageInstaller

    def __init__(self, options):
        self.options = options
        self.find_links = options['urls'].as_list()
        self.broken_links = []  # List of links that doesn't works.
        self.max_depth = options.get('max_depth', '4').as_int()
        self.links = {}
        self.downloading_links = {}
        self.lock = threading.Lock()
        self.cache = Installers()
        self.downloader = DownloadManager(self.get_download_directory())

    def download_link(self, url):
        """Effectively download a URL in the link cache.
        """
        self.lock.acquire()
        if url in self.downloading_links:
            self.lock.release()
            # We are looking at this page, just wait.
            self.downloading_links[url].wait()
            return url in self.links

        # Add a Event and wait.
        self.downloading_links[url] = threading.Event()
        self.lock.release()

        try:
            links = get_links(url, lower=True)
        except NetworkError:
            logger.warn("URL '%s' inaccessible, mark as broken.", url)
            self.broken_links.append(url)
        else:
            self.links[url] = links
            # Add found software in the cache
            self.cache.extend(get_installers_from_links(self, links))

        self.downloading_links[url].set()
        return url in self.links

    def get_links(self, url):
        """Load links from the given URL if needed. Return True upon success.
        """
        if url in self.broken_links:
            logger.debug("Ignoring broken url '%s'.", url)
            return False
        if url not in self.links:
            return self.download_link(url)
        return True

    def get_download_directory(self):
        """Return the created download directory.
        """
        directory = self.options['download_directory'].as_text()
        create_directory(directory)
        return directory

    def get_packages(self, link, search, depth=0):
        if depth > self.max_depth:
            return None

        if not self.get_links(link):
            # The given link is not accessible.
            return None

        # Look for a software in the cache
        packages = search.query()
        if packages:
            return packages

        # No software, look for an another link with the name of the software
        links = self.links[link]
        if search.key in links:
            return self.get_packages(links[search.key], search, depth + 1)
        elif depth:
            # Ok, look for links that contains download url (pypi compliant)
            for label in links:
                if DOWNLOAD_URL.match(label):
                    link = links[label]
                    if link not in self.links:
                        candidates = self.get_packages(link, search, depth + 1)
                        if candidates is not None:
                            return candidates
        return None

    def initialize(self, first_time):
        pass

    def available(self, configuration):
        setup_config = configuration['setup']
        offline = 'offline' in setup_config and \
            setup_config['offline'].as_bool()
        return not offline

    def search(self, requirement, interpretor):
        search = RemoteSearchQuery(requirement, interpretor, self.cache)

        for find_link in self.find_links:
            __status__ = u"Locating remote source for %s on %s" % (
                search.name, find_link)
            packages = self.get_packages(find_link, search)
            if packages is not None:
                return packages
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<Downloader Source for %s>' % str(list(self.find_links))


class LocalSource(object):
    """This represent a directory with a list of archives, that can be
    used to install software.
    """
    factory = UninstalledPackageInstaller
    type = 'Archive Source'
    finder = get_installers_from_directory

    def __init__(self, options):
        __status__ = u"Initializing local software sourcs."
        self.options = options
        self.paths = options['directory'].as_list()
        self.installers = Installers()

    def initialize(self, first_time):
        __status__ = u"Analysing local software source %s." % (
            ', '.join(self.paths))
        for path in self.paths:
            if first_time:
                create_directory(path)
            self.installers.extend(self.finder(path))

    def available(self, configuration):
        return True

    def search(self, requirement, interpretor):
        __status__ = u"Locating local source for %s in %s." % (
            requirement, ', '.join(self.paths))
        pyversion = interpretor.get_pyversion()
        platform = interpretor.get_platform()
        packages = self.installers.get_installers_for(
            requirement, pyversion, platform)
        if packages:
            return packages
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<%s at %s>' % (self.type, ', '.join(self.paths))


class EggsSource(LocalSource):
    """This manage installed sources.
    """
    factory = PackageInstaller
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
        self.enabled = None
        self.develop = options.get('develop', 'on').as_bool()
        if 'available' in options:
            self.enabled = options['available'].as_list()
        self.factory = ExtractedPackageInstaller
        if self.develop:
            self.factory = PackageInstaller

    def _sources(self):
        for name in self.options['sources'].as_list():
            section = self.options.configuration['vcs:' + name]
            for package, info in section.items():
                yield VCSCheckout(
                    package, info, info.as_words(), self.directory)

    def initialize(self, first_time):
        __status__ = u"Preparing remote development sources."
        if not first_time:
            return
        sources = list(self._sources())
        if sources:
            VCS.initialize()
            create_directory(self.directory)
            for source in sources:
                self.sources[source.name] = VCS(source)

    def available(self, configuration):
        # This source provider is always available
        return True

    def search(self, requirement, interpretor):
        name = requirement.name
        if name in self.sources:
            if self.enabled and name not in self.enabled:
                raise PackageNotFound(requirement)
            source = self.sources[name]()
            installer = self.factory(self, name=name, path=source.directory)
            packages = Installers([installer]).get_installers_for(requirement)
            if packages:
                return packages
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<VCSSource at %s>' % (self.directory)


class FakeSource(object):
    """This source fake packages without installing them.
    """

    def __init__(self, options):
        __status__ = u"Initializing fake source."
        self.options = options
        self.installers = Installers()
        for requirement in Requirements.parse(
            options.get('packages', '').as_list()):
            self.installers.add(FakeInstaller(requirement))

    def initialize(self, first_time):
        pass

    def available(self, configuration):
        # This source provider is available if there are packages
        return bool(len(self.installers))

    def search(self, requirement, interpretor):
        packages = self.installers.get_installers_for(requirement)
        if packages:
            return packages
        raise PackageNotFound(requirement)

    def __repr__(self):
        return '<FakeSource>'


SOURCE_PROVIDERS = {'local': LocalSource,
                    'remote': RemoteSource,
                    'eggs': EggsSource,
                    'vcs': VCSSource,
                    'fake': FakeSource}

class Sources(object):
    """This manage software sources.
    """

    def __init__(self, configuration, section_name='setup'):
        __status__ = u"Initializing software sources."
        self.sources = []
        self.available_sources = []
        self.configuration = configuration
        for source_name in configuration[section_name]['sources'].as_list():
            source_config = configuration['source:' + source_name]
            type = source_config['type'].as_text()
            if type not in SOURCE_PROVIDERS:
                raise ConfigurationError(
                    u'Unknow source type %s for %s' % (
                        type, source_name))
            self.sources.append(SOURCE_PROVIDERS[type](source_config))
        self._initialized = False

    def initialize(self):
        if self._initialized:
            for source in self.available_sources:
                source.initialize(False)
            return
        for source in self.sources:
            if not source.available(self.configuration):
                continue
            source.initialize(True)
            self.available_sources.append(source)
        self._initialized = True

    def search(self, requirement, interpretor):
        """Search of a given package at the given location.
        """
        for source in self.available_sources:
            try:
                return source.search(requirement, interpretor)
            except PackageNotFound:
                continue
        raise PackageNotFound(repr(requirement))

    def __repr__(self):
        return '<Source %s>' % ', '.join(map(repr, self.sources))

