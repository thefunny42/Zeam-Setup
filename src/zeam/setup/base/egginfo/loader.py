
import os

from zeam.setup.base.egginfo.read import read_pkg_requires, read_pkg_info
from zeam.setup.base.egginfo.read import read_pkg_entry_points
from zeam.setup.base.version import Version


class EggLoader(object):

    def __init__(self, distribution):
        self.distribution = distribution

    def load(self):
        path = self.distribution.path

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

