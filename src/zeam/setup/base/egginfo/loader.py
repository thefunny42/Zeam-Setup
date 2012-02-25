
import os
import shutil

from zeam.setup.base.egginfo.read import read_pkg_requires, read_pkg_info
from zeam.setup.base.egginfo.read import read_pkg_entry_points, read_native_libs
from zeam.setup.base.version import Version


class EggLoader(object):

    def __init__(self, path, egg_info, distribution,
                 source_path=None, execute=None):
        self.path = path
        self.source_path = source_path or path
        self.egg_info = egg_info
        self.distribution = distribution
        self.execute = execute

    def load(self):
        pkg_info = read_pkg_info(self.egg_info)
        self.distribution.package_path = self.path
        self.distribution.name = pkg_info['name']
        self.distribution.version = Version.parse(pkg_info['version'])
        self.distribution.summary = pkg_info.get('summary', '')
        self.distribution.author = pkg_info.get('author', '')
        self.distribution.author_email = pkg_info.get('author-email', '')
        self.distribution.license = pkg_info.get('license', '')
        self.distribution.classifiers = pkg_info.get('classifier', '')
        self.distribution.path = os.path.abspath(self.source_path)
        self.distribution.entry_points = read_pkg_entry_points(self.egg_info)
        self.distribution.requirements, self.distribution.extras = \
            read_pkg_requires(self.egg_info)
        self.distribution.extensions = read_native_libs(self.egg_info)
        return self.distribution

    def install(self, install_path):
        if install_path != self.distribution.path:
            shutil.copytree(self.distribution.path, install_path)


class EggLoaderFactory(object):
    """Load an egg package.
    """

    def __init__(self, options):
        self.options = options

    def __call__(self, distribution, path, interpreter, trust=-99):
        egg_info = os.path.join(path, 'EGG-INFO')
        if os.path.isdir(egg_info):
            return EggLoader(path, egg_info, distribution)
        return None
