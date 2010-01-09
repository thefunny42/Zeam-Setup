
from StringIO import StringIO
import logging
import os
import stat
import sys
import pprint
import re
import operator

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.error import PackageError, InstallationError

logger = logging.getLogger('zeam.setup')

VERSION_PARTS = re.compile(r'(\d+|[a-z]+|\.|-)')
VERSION_REPLACE = {'pre':'c', 'preview':'c', '-':'final-', 'rc':'c',}.get
REQUIREMENT_PARSE = re.compile(
    r'(?P<operator>[<>=!]=)\s*(?P<version>[\da-z.\-]+)\s*,?')
REQUIREMENT_OPERATORS = {'==': operator.eq, '>=': operator.ge,
                         '!=': operator.ne, '<=': operator.le}.get
SCRIPT_TEMPLATE = """#!%(executable)s

import sys
sys.path[0:0] = %(modules_path)s

%(script)s
"""

class Version(object):
    """Represent a version of a software.
    """

    def __init__(self, *version):
        self.version = version

    @classmethod
    def parse(klass, version):
        # This algo comes from setuptools
        def split_version_in_parts():
            for part in VERSION_PARTS.split(version.lower()):
                if not part or part == '.':
                    continue
                part = VERSION_REPLACE(part, part)
                if part[0] in '0123456789':
                    yield part.zfill(8)
                else:
                    yield '*' + part
            yield '*final'

        parsed_version = []
        for part in split_version_in_parts():
            if part.startswith('*'):
                if part < '*final':   # remove '-' before a prerelease tag
                    while parsed_version and parsed_version[-1] == '*final-':
                        parsed_version.pop()
                # remove trailing zeros from each series of numeric parts
                while parsed_version and parsed_version[-1] == '00000000':
                    parsed_version.pop()
            parsed_version.append(part)
        return klass(*parsed_version)

    def __str__(self):
        rendered_version = []
        need_dot = False
        for part in self.version[:-1]:
            if part[0] == '*':
                rendered_version.append(part[1:])
            elif need_dot:
                rendered_version.append('.')
            need_dot = False
            if part[0] == '0':
                rendered_version.append(part.strip('0'))
                need_dot = True
        return ''.join(rendered_version)


class Requirements(object):
    """Represent a list of requirements.
    """

    def __init__(self, *requirements):
        self.requirements = requirements

    def match(self, release):
        return False

    @classmethod
    def parse(klass, requirements):
        parsed_requirements = []
        # We can parse a list of requirements
        if not isinstance(requirements, list):
            requirements = [requirements,]

        # Parse requirements
        for requirement in requirements:
            for operator, version in REQUIREMENT_PARSE.findall(requirement):
                parsed_requirements.append(
                    (REQUIREMENT_OPERATORS(operator),
                     Version.parse(version)))
        return klass(*parsed_requirements)

    def __str__(self):
        return ''


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
    """Represent a release of a software.
    """

    def __init__(self, name, version, format, url,
                 pyversion=None, platform=None):
        self.name = name
        self.version = Version.parse(version)
        self.format = format
        self.url = url
        self.pyversion = pyversion
        self.platform = platform
        self.path = None
        self.entry_points = {}
        self.requires = []

    def is_active(self):
        """Return true of the release is currently usable by the
        current process.
        """
        return self.path in sys.path

    def activate(self):
        """Activate the release in the current process.
        """
        if self.path is None:
            raise InstallationError(
                self.name, u'Trying to activate a non-installed package')
        if self.is_active():
            return
        # XXX Should check dependencies here as well
        sys.path.insert(len(sys.path) and 1 or 0, self.path)

    def get_entry_point(self, group, name):
        """Load the entry point called name in the given group and return it.
        """
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
                u'Invalid module %s for entry point %s %s:%s' % (
                    python_path, group, self.name, name))
        try:
            entry_point = getattr(python_module, attribute)
        except AttributeError:
            raise PackageError(
                self.name,
                u'Invalid attribute %s in module %s ' \
                    'for entry point %s %s:%s' % (
                    attribute, python_path, group, self.name, name))
        return entry_point

    def __repr__(self):
        return '<%s for %s version %s>' % (
            self.__class__.__name__,self.name, self.version)


class DownloableRelease(Release):
    """A release that you can download.
    """
    pass


class DevelopmentRelease(Release):
    """A development release located on the file system.
    """

    def __init__(self, path=None, config=None):
        if config is None:
            if path is not None:
                config = self.__load_egg_config(path)
            else:
                raise PackageError(
                    u'Need a path or a config to create a development release')
        elif path is None:
            path = config.get_cfg_directory()
        self.__load_egg_info(config, path)

    def __load_egg_config(self, path):
        path = os.path.abspath(path)
        setup_cfg_path = os.path.join(path, 'setup.cfg')
        if not os.path.isfile(setup_cfg_path):
            raise PackageError(path, 'No setup.cfg information')
        return Configuration.read(setup_cfg_path)

    def __load_egg_info(self, config, path):
        egginfo = config['egginfo']

        self.name = egginfo['name'].as_text()
        self.version = Version.parse(egginfo['version'].as_text())
        self.format = None
        self.url = path
        self.pyversion = None
        self.platform = None
        self.requires = Requirements.parse(
            egginfo.get('requires', '').as_list())

        # Source path of the extension
        source_path = os.path.join(path, egginfo.get('source', '.').as_text())
        if not os.path.isdir(source_path):
            raise PackageError(path, 'Invalid source path "%s"' % source_path)
        self.path = source_path

        # Entry points
        self.entry_points = {}
        entry_points = egginfo.get('entry_points', None)
        if entry_points is not None:
            for category_name in entry_points.as_list():
                info = config['entry_points:' + category_name]
                self.entry_points[category_name] = info.as_dict()


class Environment(object):
    """Represent a set of released packages that can be used together.
    """

    def __init__(self, default_executable=None):
        self.releases = {}
        self.default_executable = default_executable

    def add(self, release):
        """Try to add a new release in the environment.
        """
        if not isinstance(release, Release):
            raise ValueError(u'Can only add release to an environment')
        if release.name not in self.releases:
            # XXX look for requires
            self.releases[release.name] = release
        else:
            raise InstallationError(
                u'Release %s and %s added in the environment' % (
                    repr(release), repr(self.releases[release.name])))

    def get_entry_point(self, group, name):
        """Return the entry point value called name for the given group.
        """
        name_parts = name.split(':')
        package = name_parts[0]
        if len(name_parts) == 1:
            entry_name = 'default'
        elif len(name_parts) == 2:
            entry_name = name_parts[1]
        else:
            InstallationError('Invalid entry point designation %s' % name)
        if package not in self.releases:
            raise PackageError(u"Package %s not available" % package)
        release = self.releases[package]
        return release.get_entry_point(group, entry_name)

    def list_entry_points(self, group, *package_names):
        """List package package_name entry point in the given group.
        """
        if not package_names:
            package_names = self.releases.keys()
        entry_points = {}
        for package_name in package_names:
            if package_name not in self.releases:
                raise PackageError(
                    u"No package called %s in the environment" % package_name)
            package = self.releases[package_name]
            package_entry_points = package.entry_points.get(group, None)
            if package_entry_points is not None:
                for name, destination in package_entry_points.items():
                    if name in entry_points:
                        raise PackageError(
                            u"Conflict between entry points called %s" % name)
                    entry_points[name] = {'destination': destination,
                                          'name': package_name + ':' + name}
        return entry_points

    def create_script(self, script_path, script_body, executable=None):
        """Create a script at the given path with the given body.
        """
        if executable is None:
            executable = self.default_executable
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
