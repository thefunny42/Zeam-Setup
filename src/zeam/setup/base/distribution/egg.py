
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
        if not line:
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
    return {}


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
        self.entry_points = {}
        self.requirements, self.extras = read_pkg_requires(egg_info)
