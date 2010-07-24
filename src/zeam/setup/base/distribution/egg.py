
import os

from zeam.setup.base.distribution.release import Release
from zeam.setup.base.error import PackageError
from zeam.setup.base.version import Requirements, Version


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
        if line[0].isupper():
            if key is not None and value is not None:
                add_metadata(key, value)
            key, value = line.split(':', 1)
        else:
            if line[0].isspace():
                line = line[1:]
            if key is None or value is None:
                raise PackageError('Invalid PKG-INFO file at %s' % path)
            value += '\n' + line
    if key is not None:
        add_metadata(key, value)
    return metadata


def read_pkg_requires(path):
    """Read a package requires.txt
    """
    try:
        data = open(os.path.join(path, 'requires.txt'), 'r')
    except IOError:
        return Requirements(), {}
    lines = []
    requires = []
    extras = {}
    current = None
    for line in data.readlines():
        line = line.strip()
        if not line or line[0] in '#;':
            continue
        if line[0] == '[' and line[-1] == ']':
            # New extra
            if current is None:
                requires = lines
            else:
                extras[current] = Requirements.parse(lines)
            lines = []
            current = line[1:-1]
        else:
            lines.append(line)
    # Store last extra
    if current is None:
        requires = lines
    else:
        extras[current] = Requirements.parse(lines)
    return Requirements.parse(requires), extras


def read_pkg_entry_points(path):
    """Read pkg-info entry points file.
    """
    try:
        data = open(os.path.join(path, 'entry_points.txt'), 'r')
    except IOError:
        return {}
    entry_points = {}
    points = {}
    section_name = None
    for line_number, line in enumerate(data.readlines()):
        line = line.strip()
        if not line or line[0] in '#;':
            continue
        if line[0] == '[' and line[-1] == ']':
            if section_name is not None:
                entry_points[section_name] = points
            points = {}
            section_name = line[1:-1]
        else:
            error_msg = u'Invalid line %d of entry_points.txt file ' \
                u'in EGG-INFO directory at %s' % (line_number, path)
            if section_name is None:
                raise PackageError(error_msg)
            parts = line.split('=')
            if len(parts) != 2:
                raise PackageError(error_msg)
            name = parts[0].strip()
            module = parts[1].strip()
            if not name or not module:
                raise PackageError(error_msg)
            if name not in points:
                points[name] = module
            else:
                raise PackageError("Duplicate entry points %s defined at %s" % (
                        name, path))
    if section_name is not None and points:
        entry_points[section_name] =  points
    return entry_points


class EggRelease(Release):
    """A release already present in the environment packaged as an
    egg.
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
        self.entry_points = read_pkg_entry_points(egg_info)
        self.requirements, self.extras = read_pkg_requires(egg_info)

    def install(self, directory, interpretor, install_missing, archive=None):
        for requirement in self.requirements:
            install_missing(requirement)
        return self
