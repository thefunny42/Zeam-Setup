
import os

from zeam.setup.base.egginfo.read import read_pkg_requires, read_pkg_info
from zeam.setup.base.egginfo.read import read_pkg_entry_points
from zeam.setup.base.version import Version


class EggLoader(object):

    def __init__(self, path, egg_info):
        self.path = path
        self.egg_info = egg_info

    def load(self, distribution, interpretor):
        pkg_info = read_pkg_info(self.egg_info)
        distribution.package_path = self.path
        distribution.name = pkg_info['name']
        distribution.version = Version.parse(pkg_info['version'])
        distribution.summary = pkg_info.get('summary', '')
        distribution.author = pkg_info.get('author', '')
        distribution.author_email = pkg_info.get('author-email', '')
        distribution.license = pkg_info.get('license', '')
        distribution.classifiers = pkg_info.get('classifier', '')
        distribution.path = os.path.abspath(self.path)
        distribution.entry_points = read_pkg_entry_points(self.egg_info)
        distribution.requirements, distribution.extras = \
            read_pkg_requires(self.egg_info)
        return distribution


class EggLoaderFactory(object):

    def available(self, path):
        egg_info = os.path.join(path, 'EGG-INFO')
        if os.path.isdir(egg_info):
            return EggLoader(path, egg_info)
        return None
