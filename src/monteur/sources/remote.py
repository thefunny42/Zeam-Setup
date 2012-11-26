
import logging
import os
import re
import threading
import urlparse
import HTMLParser

from monteur.sources import (
    Installers, PackageInstallers, Source, Context)
from monteur.sources.utils import (
    parse_filename,
    UninstalledPackageInstaller)
from monteur.download import DownloadManager
from monteur.error import PackageDistributionError
from monteur.error import NetworkError, DownloadError
from monteur.utils import open_uri, is_remote_uri, create_directory

logger = logging.getLogger('monteur')

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

    def install(self, path, install_dependencies):
        try:
            archive = self.context.downloader.download(
                self.url, ignore_content_types=['text/html'])
        except DownloadError, e:
            logger.warn(
                u"%s doesn't seem to be a valid package, ignoring it.",
                self.url)
            self.context.mark_as_broken(self)
            raise PackageDistributionError(*e.args)
        return super(UndownloadedPackageInstaller, self).install(
            path, install_dependencies, archive)


class URL(object):
    """A remote url.
    """

    def __init__(self, url, filename=None, name=None, rel=None):
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
        return "<URL '%s'>" % (self.url)

    @property
    def is_followable(self):
        return DOWNLOAD_NAME.match(self.name) or (self.rel in FOLLOW_REL_LINK)

    def follow(self, context):
        """Follow this link to find more.
        """
        urls = []
        informations = []
        stream = open_uri(self.url)
        try:
            content_type = stream.headers.get('content-type', '').split(';')[0]
            if content_type not in ['text/html']:
                raise NetworkError('Not HTML', self.url)
            parser = LinkParser(self.url)
            parser.feed(stream.read())
        except HTMLParser.HTMLParseError:
            logger.warn("Discarding unreadable HTML page '%s'", self.url)
            return urls, informations
        finally:
            stream.close()
        for url, filename, name, rel in parser.links:
            if context.is_disabled_link(url, True):
                continue
            information = parse_filename(filename, url=url)
            if information:
                informations.append(information)
            else:
                urls.append(self.__class__(url, filename, name, rel))
        return urls, informations


class RequirementSearch(object):
    """Bind a search for a requirement.
    """
    # Condition to be tested in order to follow a download link
    conditions = [
        lambda self, link, depth: self.key == link.key,
        lambda self, link, depth: depth and link.is_followable,
        lambda self, link, depth: self.criteria.match(link.key)]

    def __init__(self, context, requirement):
        self.context = context
        self.name = requirement.name
        self.key = requirement.name.lower()
        self.criteria = re.compile(r'.*\b%s\b.*' % re.escape(self.key))
        self.requirement = requirement

    def search(self, link, depth=0):
        if depth > self.context.max_depth:
            return None

        __status__ = u"Locating remote source for %s on %s" % (self.name, link)
        if not self.context.follow_link(link):
            # The given link is not accessible.
            return None

        # Look for a software in the cache
        packages = self.context.search(self.requirement)
        if packages:
            return packages

        # No software, look for an another link to follow
        links = self.context.links[link]
        for condition in self.conditions:
            for link in links:
                if condition(self, link, depth):
                    packages = self.search(link, depth + 1)
                    if packages:
                        return packages
        return None


class RemoteContext(Context):

    def __init__(self, source, interpretor, priority, trust=0):
        super(RemoteContext, self).__init__(source, interpretor, priority, trust)
        self.find_links = source.find_links
        self.disallow_urls = source.disallow_urls
        self.allow_urls = source.allow_urls
        self.max_depth = source.max_depth
        self.broken_links = set([])  # List of links that doesn't works.
        self.links = {}
        self.downloading_links = {}
        self.lock = threading.Lock()
        self.cache = Installers()
        self.downloader = DownloadManager(source.get_download_directory())

    def search(self, requirement):
        """Search if there is a match for a requirement in the cache.
        """
        return self.cache.get_installers_for(
            requirement, self.pyversion, self.platform)

    def mark_as_broken(self, installer):
        """Mark an installer as broken so it won't be found again.
        """
        self.broken_links.add(installer.url)
        self.cache.remove(installer)

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
                links, informations = url.follow(self)
            except NetworkError:
                logger.warn("URL '%s' inaccessible, mark as broken.", url)
                self.broken_links.add(url)
            else:
                # Add found links and installers
                self.links[url] = links
                for detail in informations:
                    self.cache.add(UndownloadedPackageInstaller(self, **detail))
        finally:
            self.downloading_links[url].set()
        return url in self.links

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


class RemoteSource(Source):
    """Download software from da internet, in order to install it.
    """
    Context = RemoteContext
    TRUST = -99

    def __init__(self, *args):
        __status__ = u"Initializing remote software source."
        super(RemoteSource, self).__init__(*args)
        self.find_links = map(lambda url: URL(url), self.options['urls'].as_list())
        self.disallow_urls = self.options.get('disallow_urls', '').as_list()
        self.allow_urls = self.options.get('allow_urls', '').as_list()
        self.max_depth = self.options.get('max_depth', '4').as_int()

    def get_download_directory(self):
        """Return the created download directory.
        """
        directory = self.options['download_directory'].as_text()
        create_directory(directory)
        return directory

    def prepare(self, context):
        setup = self.options.configuration['setup']
        if 'offline' not in setup or not setup['offline'].as_bool():

            def query(requirement, strategy):
                unique = requirement.is_unique()
                candidates = PackageInstallers(requirement.key)
                query = RequirementSearch(context, requirement)

                for find_link in self.find_links:
                    candidates.extend(query.search(find_link))
                    if unique and candidates:
                        return candidates
                return candidates

            return query
        return None

    def __repr__(self):
        return '<RemoteSource for %s>' % str(list(self.find_links))
