
import logging
import re
import threading


from zeam.setup.base.sources import Installers
from zeam.setup.base.sources.utils import (
    get_installer_from_name,
    UninstalledPackageInstaller)
from zeam.setup.base.download import DownloadManager
from zeam.setup.base.error import PackageNotFound
from zeam.setup.base.error import NetworkError
from zeam.setup.base.utils import get_links, create_directory


logger = logging.getLogger('zeam.setup')

DOWNLOAD_URL = re.compile(r'.*download.*', re.IGNORECASE)


def get_installers_from_links(source, links):
    """Get downloadable software from links.
    """
    for name, url in links.iteritems():
        installer = get_installer_from_name(source, name, url=url)
        if installer is not None:
            yield installer


class UndownloadedPackageInstaller(UninstalledPackageInstaller):
    """A release that you can download.
    """

    def install(self, path, interpretor, install_dependencies):
        archive = self.source.downloader.download(self.url)
        return super(UndownloadedPackageInstaller, self).install(
            path, interpretor, install_dependencies, archive)


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
            try:
                links = get_links(url, lower=True)
            except NetworkError:
                logger.warn("URL '%s' inaccessible, mark as broken.", url)
                self.broken_links.append(url)
            else:
                self.links[url] = links
                # Add found software in the cache
                self.cache.extend(get_installers_from_links(self, links))
        finally:
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
