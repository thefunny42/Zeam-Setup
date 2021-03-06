
import logging
import os
import shutil

from monteur.configuration import Configuration
from monteur.distribution.manifest import parse_manifest
from monteur.egginfo.write import write_egg_info
from monteur.error import PackageError
from monteur.python import PythonInterpreter
from monteur.recipe.utils import Paths
from monteur.setuptools.autotools import AutomakeBuilder
from monteur.version import Version, Requirements

logger = logging.getLogger('monteur')

builder = AutomakeBuilder()


def install_file(source_file, destination_file):
    destination_directory = os.path.dirname(destination_file)
    if not os.path.isdir(destination_directory):
        os.makedirs(destination_directory)
    shutil.copy2(source_file, destination_file)


class SetupLoader(object):

    def __init__(self, configuration, distribution, interpretor=None):
        self.path = configuration.get_cfg_directory()
        self.configuration = configuration
        self.distribution = distribution
        if interpretor is None:
            interpretor = PythonInterpreter.detect(
                configuration['setup']['python_executable'].as_text())
        self.interpretor = interpretor

    def load(self):
        egginfo = self.configuration['egginfo']
        self.distribution.name = egginfo['name'].as_text()
        self.distribution.version = Version.parse(egginfo['version'].as_text())
        self.distribution.summary = egginfo.get('summary', '').as_text()
        self.distribution.author = egginfo.get('author', '').as_text()
        self.distribution.author_email = egginfo.get(
            'author_email', '').as_text()
        self.distribution.license = egginfo.get('license', '').as_text()
        self.distribution.classifiers = egginfo.get('classifier', '').as_list()
        self.distribution.format = None
        self.distribution.pyversion = None
        self.distribution.platform = None
        self.distribution.requirements = Requirements.parse(
            egginfo.get('requires', '').as_list())
        self.distribution.extras = {}

        # Source path of the extension
        path = os.path.join(self.path, egginfo.get('source', '.').as_text())
        if not os.path.isdir(path):
            raise PackageError(path, 'Invalid source path "%s"' % path)
        self.distribution.path = os.path.abspath(path)
        self.distribution.package_path = self.path

        # Entry points
        self.distribution.entry_points = {}
        entry_points = egginfo.get('entry_points', None)
        if entry_points is not None:
            for category_name in entry_points.as_list():
                info = self.configuration['entry_points:' + category_name]
                self.distribution.entry_points[category_name] = info.as_dict()

        return self.distribution

    def build(self, path):
        if self.distribution.extensions:
            builder.build(self.distribution, path, self.interpretor)

    def install(self, path):
        egg_info = self.configuration['egginfo']
        manifest_url = egg_info['manifest'].as_file()
        files = Paths(verify=False)
        files.listdir(self.distribution.package_path)
        prefixes = []
        if 'source' in egg_info:
            prefixes = [egg_info['source'].as_text()]
        for filename, info in files.as_manifest(*parse_manifest(manifest_url),
                                                 prefixes=prefixes):
            install_file(info['full'], os.path.join(path, filename))

        # XXX This needs review
        # if self.distribution.extensions:
        #     builder.install(
        #         self.distribution, install_path, self.interpretor)

        write_egg_info(self.distribution, package_path=path)


class SetupLoaderFactory(object):
    """Load a monteur package.
    """

    def __init__(self, options):
        self.options = options

    def __call__(self, distribution, path, interpretor, trust=-99):
        setup_cfg = os.path.join(path, 'monteur.cfg')
        if os.path.isfile(setup_cfg):
            configuration = Configuration.read(setup_cfg)
            if 'egginfo' in configuration.sections:
                return SetupLoader(configuration, distribution, interpretor)
            logger.debug(
                u"Missing monteur package configuration in %s",
                setup_cfg)
        return None

