
import re
import os

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.error import InstallationError
from zeam.setup.base.utils import get_links


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
            yield Release(name,
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
            links = get_links(find_links)
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
        links = self.__links_cache[find_links]
        if name in links:
            return self.__download(name, links[name], depth + 1)
        return None

    def download(self, name, version=None):
        name = name.lower()
        for find_link in find_links:
            stuff = self.__download(name, find_link, version=version)

    def __repr__(self):
        return '<Downloader for %s>' % str(list(self.find_links))


class ArchiveDirectory(object):

    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return '<Archive Directory at %s>' % self.path


class Software(object):

    def __init__(self, name):
        self.name = name
        self.releases = []

    def add(self, release):
        if release.name != self.name:
            raise InstallationError('Invalid release added to collection')
        self.releases.append(release)

    def __repr__(self):
        return '<Software %s>' % self.name


class Release(object):

    def __init__(self, name, version, format, url,
                 pyversion=None, platform=None):
        self.name = name
        self.version = version
        self.format = format
        self.url = url
        self.pyversion = pyversion
        self.platform = platform
        self.path = None

    def __repr__(self):
        return '<%s for %s version %s>' % (
            self.__class__.__name__,self.name, self.version)


class DevelopmentRelease(Release):

    def __init__(self, path):
        self.__load_egg_info(path)

    def __load_egg_info(self, path):
        path = os.path.abspath(path)
        setup_cfg_path = os.path.join(path, 'setup.cfg')
        if not os.path.isfile(setup_cfg_path):
            raise InstallationError('%s: No setup.cfg information' % path)
        setup_cfg = Configuration.read(setup_cfg_path)
        egginfo = setup_cfg['egginfo']

        self.name = egginfo['name'].as_text()
        self.version = egginfo['version'].as_text()
        self.format = None
        self.url = path
        self.pyversion = None
        self.platform = None
        self.path = path


class Environment(object):

    def __init__(self):
        self.releases = {}

    def add(self, release):
        if not isinstance(release, Release):
            raise ValueError(u'Can only add release to an environment')
        if release.name not in self.releases:
            self.releases[release.name] = release
        else:
            raise Installation(
                u'Release %s and %s added in the environment' % (
                    repr(release), repr(self.releases[release.name])))
