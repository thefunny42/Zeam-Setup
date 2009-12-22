
from StringIO import StringIO
import logging
import re
import os
import stat
import sys
import pprint

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.error import PackageError, InstallationError
from zeam.setup.base.utils import get_links

logger = logging.getLogger('zeam.setup')

RELEASE_TARBALL = re.compile(
    r'^(?P<name>[^-]+)-(?P<version>.*)'
    r'(-py(?P<pyversion>[^-])(-(?P<platform>[\w]+))?)?'
    r'\.(?P<format>zip|egg|tgz|tar\.gz)$',
    re.IGNORECASE)

SCRIPT_TEMPLATE = """#!%(executable)s

import sys
sys.path[0:0] = %(modules_path)s

%(script)s
"""


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
        self.entry_points = {}

    def is_active(self):
        return self.path in sys.path

    def activate(self):
        if self.path is None:
            raise InstallationError(
                self.name, 'Trying to activate a non-installed package')
        if self.is_active():
            return
        # XXX Should check dependencies here as well
        sys.path.insert(len(sys.path) and 1 or 0, self.path)

    def get_entry_point(self, group, name):
        if group not in self.entry_points:
            return None
        if name not in self.entry_points[group]:
            return None

        # Activate plugin if needed
        if not self.is_active():
            self.activate()

        # Load the entry point
        (python_path, attribute) = self.entry_points[group][name].split(':')
        try:
            python_module = __import__(
                python_path, globals(), globals(), [attribute])
        except ImportError:
            raise PackageError(
                self.name,
                'Invalid module %s for entry point %s %s:%s' % (
                    python_path, group, self.name, name))
        try:
            entry_point = getattr(python_module, attribute)
        except AttributeError:
            raise PackageError(
                self.name,
                'Invalid attribute %s in module %s for entry point %s %s:%s' % (
                    attribute, python_path, group, self.name, name))
        return entry_point

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
            raise PackageError(path, 'No setup.cfg information')
        setup_cfg = Configuration.read(setup_cfg_path)
        egginfo = setup_cfg['egginfo']

        self.name = egginfo['name'].as_text()
        self.version = egginfo['version'].as_text()
        self.format = None
        self.url = path
        self.pyversion = None
        self.platform = None

        # Source path of the extension
        source_path = os.path.join(path, egginfo.get('source', '.').as_text())
        if not os.path.isdir(source_path):
            raise PackageError(path, 'Invalid source path "%s"' % source)
        self.path = source_path

        # Entry points
        self.entry_points = {}
        entry_points = egginfo.get('entry_points', None)
        if entry_points is not None:
            for category_name in entry_points.as_list():
                info = setup_cfg['entry_points:' + category_name]
                self.entry_points[category_name] = info.as_dict()


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

    def get_entry_point(self, group, name):
        name_parts = name.split(':')
        package = name_parts[0]
        if len(name_parts) == 1:
            entry_name = 'default'
        elif len(name_parts) == 2:
            entry_name = name_parts[1]
        else:
            InstallationError('Invalid entry point designation %s' % name)
        # XXX Do a keyerror if package is not there
        release = self.releases[package]
        return release.get_entry_point(group, entry_name)

    def list_entry_points(self, group, package_name):
        # XXX Do a keyerror if package is not there
        return self.releases[package_name].entry_points.get(group, None)

    def create_script(self, script_path, script_body, executable=None):
        """Create a script at the given path with the given body.
        """
        logger.info('Creating script %s' % script_path)
        modules_path = StringIO()
        printer = pprint.PrettyPrinter(stream=modules_path, indent=2)
        printer.pprint(map(lambda r: r.path, self.releases.values()))
        script_fd = open(script_path, 'w')
        script_fd.write(SCRIPT_TEMPLATE % {
                'executable': executable,
                'modules_path': modules_path.getvalue(),
                'script': script_body})
        script_fd.close()
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
        return script_path
