
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
REQUIREMENT_NAME_PARSE = re.compile(
    r'^(?P<name>[\w.]+)\s*(?P<requirements>.*)$')
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

    def __lt__(self, other):
        return self.version < other

    def __gt__(self, other):
        return self.version > other

    def __eq__(self, other):
        return self.version == other

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
                rendered_version.append(part.strip('0') or '0')
                need_dot = True
        return ''.join(rendered_version)


class Requirement(object):
    """Represent a requirement.
    """

    def __init__(self, name, versions):
        self.name = name
        self.versions = versions

    @classmethod
    def parse(cls, requirement):
        groups = REQUIREMENT_NAME_PARSE.match(requirement)
        version_requirements = []
        for operator, version in REQUIREMENT_PARSE.findall(
            groups.group('requirements')):
            version_requirements.append(
                (REQUIREMENT_OPERATORS(operator),
                 Version.parse(version)))

        return cls(groups.group('name'), version_requirements)

    def match(self, release):
        return False

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Requirement %s>' % (self.name)


class Requirements(object):
    """Represent a list of requirements.
    """

    def __init__(self, *requirements):
        self.requirements = requirements

    @classmethod
    def parse(cls, requirements):
        parsed_requirements = []
        # We can parse a list of requirements
        if not isinstance(requirements, list):
            requirements = [requirements,]

        # Parse requirements
        for requirement in requirements:
            parsed_requirements.append(
                Requirement.parse(requirement))

        return cls(*parsed_requirements)

    def __str__(self):
        return ''


class Software(object):
    """A software is composed by a list of release of the same
    software.
    """

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
        self.summary = ''
        self.author = ''
        self.author_email = ''
        self.license = ''
        self.classifiers = []
        self.format = format
        self.url = url
        self.pyversion = pyversion
        self.platform = platform
        self.path = None
        self.entry_points = {}
        self.requirements = []

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


class UninstalledRelease(Release):
    """A release that you can download.
    """
    pass


def read_pkg_info(path):
    """Read the PKG-INFO file located at the given path and return the
    information as a dictionnary.
    """
    metadata = {}

    def add_metadata(key, value):
        value = value.strip()
        if value == 'UNKNOWN':
            value = ''
        key = key.strip().lower()
        if metadata.has_key(key):
            if isinstance(metadata[key], list):
                metadata[key].append(value)
            else:
                metadata[key] = [metadata[key], value]
        else:
            metadata[key] = value

    key = None
    value = None
    try:
        pkg_info = open(os.path.join(path, 'PKG-INFO'), 'r')
    except IOError:
        raise PackageError('Invalid EGG-INFO directory at %s' % path)
    for line in pkg_info.readlines():
        if line and line[0] in '#;':
            continue
        if line[0].isspace():
            if key is None and value is None:
                raise PackageError('Invalid PKG-INFO file at %s' % path)
            value += '\n' + line[0]
        else:
            if key is not None and value is not None:
                add_metadata(key, value)
            key, value = line.split(':', 1)
    if key is not None:
        add_metadata(key, value)
    return metadata


class EnvironmentRelease(Release):
    """A release already present in the environment.
    """

    def __init__(self, path):
        egg_info = os.path.join(path, 'EGG-INFO')
        pkg_info = read_pkg_info(egg_info)
        self.name = pkg_info['name']
        self.version = Version.parse(pkg_info['version'])
        self.summary = pkg_info.get('summary', '')
        self.author = pkg_info.get('author', '')
        self.author_email = pkg_info.get('author-email', '')
        self.license = pkg_info.get('license', '')
        self.classifiers = pkg_info.get('classifier', '')
        self.format = None
        self.url = None
        self.pyversion = None
        self.platform = None
        self.path = os.path.abspath(path)
        self.entry_points = {}
        self.requirements = []


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
        self.summary = egginfo.get('summary', '').as_text()
        self.author = egginfo.get('author', '').as_text()
        self.author_email = egginfo.get('author_email', '').as_text()
        self.license = egginfo.get('license', '').as_text()
        self.classifiers = egginfo.get('classifier', '').as_list()
        self.format = None
        self.url = path
        self.pyversion = None
        self.platform = None
        self.requirements = Requirements.parse(
            egginfo.get('requires', '').as_list())

        # Source path of the extension
        source_path = os.path.join(path, egginfo.get('source', '.').as_text())
        if not os.path.isdir(source_path):
            raise PackageError(path, 'Invalid source path "%s"' % source_path)
        self.path = os.path.abspath(source_path)

        # Entry points
        self.entry_points = {}
        entry_points = egginfo.get('entry_points', None)
        if entry_points is not None:
            for category_name in entry_points.as_list():
                info = config['entry_points:' + category_name]
                self.entry_points[category_name] = info.as_dict()


class DistributionSetEntry(object):
    """Cache entry in a distribution set.
    """

    def __init__(self, distribution_set, name):
        self.distribution_set = distribution_set
        self.name = name

    def resolve(self):
        """This resolves all dependencies, by finding corresponding
        releases.
        """

class DistributionSet(object):
    """Represent a possible set of releases that can be used together.
    """

    def __init__(self, source):
        self.source = source
        self.entries = {}
        self.requirements = Requirements()

    def search(self, name):
        pass


class Environment(object):
    """Represent the set of release used together.
    """

    def __init__(self, default_executable=None):
        self.installed = {}
        self.default_executable = default_executable
        self.source = None

        if self.default_executable == sys.executable:
            for path in sys.path:
                if os.path.isdir(os.path.join(path, 'EGG-INFO')):
                    self.add(EnvironmentRelease(path))

    def set_source(self, source):
        """Set the source used to find new software.
        """
        self.source = source

    def install(self, name, directory):
        # XXX Testing
        self.source.install(Requirement.parse(name), directory)

    def add(self, release):
        """Try to add a new release in the environment.
        """
        if not isinstance(release, Release):
            raise ValueError(u'Can only add release to an environment')
        if release.name not in self.installed:
            # XXX look for requires
            self.installed[release.name] = release
        else:
            installed = self.installed[release.name]
            if installed.path == release.path:
                self.installed[release.name] = release
            else:
                raise InstallationError(
                    u'Release %s and %s added in the environment' % (
                        repr(release), repr(self.installed[release.name])))

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
        if package not in self.installed:
            raise PackageError(u"Package %s not available" % package)
        release = self.installed[package]
        return release.get_entry_point(group, entry_name)

    def list_entry_points(self, group, *package_names):
        """List package package_name entry point in the given group.
        """
        if not package_names:
            package_names = self.installed.keys()
        entry_points = {}
        for package_name in package_names:
            if package_name not in self.installed:
                raise PackageError(
                    u"No package called %s in the environment" % package_name)
            package = self.installed[package_name]
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
        logger.warning('Creating script %s' % script_path)
        modules_path = StringIO()
        printer = pprint.PrettyPrinter(stream=modules_path, indent=2)
        printer.pprint(map(lambda r: r.path, self.installed.values()))
        script_fd = open(script_path, 'w')
        script_fd.write(SCRIPT_TEMPLATE % {
                'executable': executable,
                'modules_path': modules_path.getvalue(),
                'script': script_body})
        script_fd.close()
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
        return script_path
