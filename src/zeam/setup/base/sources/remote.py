
import logging
import os
import re
import threading
import urlparse
import HTMLParser

from zeam.setup.base.sources import (
    Installers, PackageInstallers, Source)
from zeam.setup.base.sources import (
    STRATEGY_QUICK, STRATEGY_UPDATE)
from zeam.setup.base.sources.utils import (
    get_installer_from_name,
    UninstalledPackageInstaller)
from zeam.setup.base.download import DownloadManager
from zeam.setup.base.error import PackageNotFound, PackageDistributionError
from zeam.setup.base.error import NetworkError, DownloadError
from zeam.setup.base.utils import open_uri, is_remote_uri, create_directory

logger = logging.getLogger('zeam.setup')

FOLLOW_REL_LINK = set(['download', 'homepage'])
DOWNLOAD_NAME = re.compile(r'\bdownload\b', re.IGNORECASE)


class LinkParser(HTMLParser.HTMLParser):
    """Collect links in an HTML file.
    """

    def __init__(self, url):
        HTMLParser.HTMLParser.__init__(self)
        self.links = []
        self._buffer = None
        self._link_attrs = None
        self._link_counter = 0

        self._url = url
        base_parts = urlparse.urlparse(url)
        self._base_uri = base_parts[0:2]
        self._relative_path = base_parts[2]
        if not self._relative_path.endswith('/'):
            self._relative_path = os.path.dirname(self._relative_path)
        elif not self._relative_path:
            self._relative_path = '/'

    def _get_link_attr(self, name):
        if self._link_attrs is not None:
            for tag, value in self._link_attrs:
                if tag == name:
                    return value
        return None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self._buffer = []
            self._link_attrs = attrs
            self._link_counter = 0
        elif self._link_counter is not None:
            self._link_counter += 1

    def handle_data(self, data):
        if self._buffer is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag):
        if self._link_counter is not None:
            if self._link_counter < 1:
                if tag != 'a':
                    logger.warn(
                        u'Invalid HTML tags in %s', self._url)
                href = self._get_link_attr('href')
                #  We discard anchors and empty href.
                if href and href[0] != '#':
                    href_parts = urlparse.urlparse(href)
                    # Convert absolute URL to absolute URI
                    if href[0] == '/':
                        href = urlparse.urlunparse(
                            self._base_uri +  href_parts[2:])
                    elif not is_remote_uri(href):
                        # Handle relative URL
                        href = urlparse.urlunparse(
                            self._base_uri +
                            ('/'.join((self._relative_path, href_parts[2])),) +
                            href_parts[3:])

                    filename = os.path.basename(href_parts[2])
                    # If the content of the link is empty, we use the last
                    # part of path.
                    if self._buffer:
                        name = ' '.join(self._buffer)
                    else:
                        name = filename
                    rel = self._get_link_attr('rel')
                    self.links.append((href, filename, name, rel),)
                self._link_counter = None
                self._link_attrs = None
                self._buffer = None
            else:
                self._link_counter -= 1


class UndownloadedPackageInstaller(UninstalledPackageInstaller):
    """A release that you can download.
    """

    def install(self, path, interpretor, install_dependencies):
        try:
            archive = self.source.downloader.download(
                self.url, ignore_content_types=['text/html'])
        except DownloadError, e:
            logger.warn(
                u"%s doesn't seem to be a valid package, ignoring it.",
                self.url)
            self.source.mark_installer_as_broken(self)
            raise PackageDistributionError(*e.args)
        return super(UndownloadedPackageInstaller, self).install(
            path, interpretor, install_dependencies, archive)


class RemoteURL(object):
    """A remote url.
    """

    def __init__(self, source, url, filename=None, name=None, rel=None):
        self.source = source
        self.url = url
        self.name = name or ''
        self.key = self.name.lower()
        self.filename = filename or ''
        if rel:
            rel = rel.lower()
        self.rel = rel

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return str(self) == str(other)

    def __str__(self):
        return str(self.url)

    def __repr__(self):
        return "<RemoteURL '%s'>" % (self.url)

    @property
    def is_followable(self):
        return DOWNLOAD_NAME.match(self.name) or (self.rel in FOLLOW_REL_LINK)

    def follow(self):
        """Follow this link to find more.
        """
        urls = []
        installers = []
        stream = open_uri(self.url)
        try:
            content_type = stream.headers.get('content-type', '').split(';')[0]
            if content_type not in ['text/html']:
                raise NetworkError('Not HTML', self.url)
            parser = LinkParser(self.url)
            parser.feed(stream.read())
        except HTMLParser.HTMLParseError:
            logger.warn("Discarding unreadable HTML page '%s'", self.url)
            return urls, installers
        finally:
            stream.close()
        for url, filename, name, rel in parser.links:
            if self.source.is_disabled_link(url, True):
                continue
            installer = get_installer_from_name(self.source, filename, url=url)
            if installer is not None:
                installers.append(installer)
            else:
                urls.append(self.__class__(
                        self.source, url, filename, name, rel))
        return urls, installers


class RemoteSearchQuery(object):
    """Bind a search for a requirement.
    """
    # Condition to be tested in order to follow a download link
    conditions = [
        lambda self, link, depth: self.key == link.key,
        lambda self, link, depth: depth and link.is_followable,
        lambda self, link, depth: self.criteria.match(link.key)]

    def __init__(self, source, requirement, interpretor):
        self.source = source
        self.name = requirement.name
        self.key = requirement.name.lower()
        self.criteria = re.compile(r'.*\b%s\b.*' % re.escape(self.key))
        self.requirement = requirement
        self.pyversion = interpretor.get_version()
        self.platform = interpretor.get_platform()

    def search(self, link, depth=0):
        if depth > self.source.max_depth:
            return None

        __status__ = u"Locating remote source for %s on %s" % (self.name, link)
        if not self.source.follow_link(link):
            # The given link is not accessible.
            return None

        # Look for a software in the cache
        packages = self.source.cache.get_installers_for(
            self.requirement, self.pyversion, self.platform)
        if packages:
            return packages

        # No software, look for an another link to follow
        links = self.source.links[link]
        for condition in self.conditions:
            for link in links:
                if condition(self, link, depth):
                    packages = self.search(link, depth + 1)
                    if packages:
                        return packages
        return None


class RemoteSource(Source):
    """Download software from da internet, in order to install it.
    """
    factory = UndownloadedPackageInstaller

    def __init__(self, *args):
        __status__ = u"Initializing remote software source."
        super(RemoteSource, self).__init__(*args)
        self.find_links = map(
            lambda url: RemoteURL(self, url), self.options['urls'].as_list())
        self.disallow_urls = self.options.get('disallow_urls', '').as_list()
        self.allow_urls = self.options.get('allow_urls', '').as_list()
        self.broken_links = set([])  # List of links that doesn't works.
        self.max_depth = self.options.get('max_depth', '4').as_int()
        self.links = {}
        self.downloading_links = {}
        self.lock = threading.Lock()
        self.cache = Installers()
        self.downloader = DownloadManager(self.get_download_directory())

    def follow_link(self, url):
        """Load links from the given URL if needed. Return True upon
        success.
        """
        if self.is_disabled_link(url):
            return False
        if url in self.links:
            return True
        self.lock.acquire()
        if url in self.downloading_links:
            self.lock.release()
            # We are looking at this page, just wait.
            self.downloading_links[url].wait()
            return url in self.links
        # Add a Event and download
        self.downloading_links[url] = threading.Event()
        self.lock.release()

        try:
            try:
                links, installers = url.follow()
            except NetworkError:
                logger.warn("URL '%s' inaccessible, mark as broken.", url)
                self.broken_links.add(url)
            else:
                # Add found links and installers
                self.links[url] = links
                self.cache.extend(installers)
        finally:
            self.downloading_links[url].set()
        return url in self.links

    def mark_installer_as_broken(self, installer):
        """Mark an installer as broken so it won't be found again.
        """
        self.broken_links.add(installer.url)
        self.cache.remove(installer)

    def is_disabled_link(self, url, verify_allow=False):
        """Return true if the given URL should not be followed,
        testing for broken links, allowed and disallowed URLs.
        """
        if url in self.broken_links:
            logger.warn("Ignoring broken URL '%s'.", url)
            return True
        if verify_allow:
            test_url = str(url).startswith
            if self.disallow_urls:
                for disallowed_url in self.disallow_urls:
                    if test_url(disallowed_url):
                        logger.warn("Ignoring disallowed URL '%s'.", url)
                        return True
            if self.allow_urls:
                for allowed_url in self.allow_urls:
                    if not test_url(allowed_url):
                        logger.warn("Ignoring not allowed URL '%s'.", url)
                        return True
        return False

    def get_download_directory(self):
        """Return the created download directory.
        """
        directory = self.options['download_directory'].as_text()
        create_directory(directory)
        return directory

    def available(self, configuration):
        setup_config = configuration['setup']
        offline = 'offline' in setup_config and \
            setup_config['offline'].as_bool()
        return not offline

    def search_quick(self, requirement, interpretor, strategy):
        # Implement strategy
        query = RemoteSearchQuery(self, requirement, interpretor)

        for find_link in self.find_links:
            packages = query.search(find_link)
            if packages is not None:
                return packages
        raise PackageNotFound(requirement)

    def search_update(self, requirement, interpretor, strategy):
        # Implement strategy
        installers = PackageInstallers(requirement.key)
        query = RemoteSearchQuery(self, requirement, interpretor)

        for find_link in self.find_links:
            found = query.search(find_link)
            if found is not None:
                installers.extend(found)
        if installers:
            return installers
        raise PackageNotFound(requirement)

    search_strategies = {
        STRATEGY_UPDATE: search_update,
        STRATEGY_QUICK: search_quick}

    def search(self, requirement, interpretor, strategy):
        search_method = self.search_strategies.get(strategy)
        if search_method is None:
            raise InstallationError('Unknow strategy %s' % STRATEGY_UPDATE)
        return search_method(self, requirement, interpretor, strategy)

    def __repr__(self):
        return '<RemoteSource for %s>' % str(list(self.find_links))
