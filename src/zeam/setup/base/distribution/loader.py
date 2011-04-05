
import logging
import os

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.version import Version, Requirements
from zeam.setup.base.error import PackageError

logger = logging.getLogger('zeam.setup')


class SetupLoader(object):

    def __init__(self, configuration):
        self.path = configuration.get_cfg_directory()
        self.configuration = configuration

    def load_configuration(self, distribution, configuration=None):
        if configuration is None:
            configuration = self.configuration
        egginfo = configuration['egginfo']
        distribution.name = egginfo['name'].as_text()
        distribution.version = Version.parse(egginfo['version'].as_text())
        distribution.summary = egginfo.get('summary', '').as_text()
        distribution.author = egginfo.get('author', '').as_text()
        distribution.author_email = egginfo.get('author_email', '').as_text()
        distribution.license = egginfo.get('license', '').as_text()
        distribution.classifiers = egginfo.get('classifier', '').as_list()
        distribution.format = None
        distribution.pyversion = None
        distribution.platform = None
        distribution.requirements = Requirements.parse(
            egginfo.get('requires', '').as_list())
        distribution.extras = {}

        # Source path of the extension
        path = os.path.join(self.path, egginfo.get('source', '.').as_text())
        if not os.path.isdir(path):
            raise PackageError(path, 'Invalid source path "%s"' % path)
        distribution.path = os.path.abspath(path)
        distribution.package_path = self.path

        # Entry points
        distribution.entry_points = {}
        entry_points = egginfo.get('entry_points', None)
        if entry_points is not None:
            for category_name in entry_points.as_list():
                info = configuration['entry_points:' + category_name]
                distribution.entry_points[category_name] = info.as_dict()
        return distribution

    def load(self, distribution, interpretor):
        return self.load_configuration(distribution)


class SetupLoaderFactory(object):
    """Load a zeam.setup package.
    """

    def available(self, path):
        setup_cfg = os.path.join(path, 'setup.cfg')
        if os.path.isfile(setup_cfg):
            configuration = Configuration.read(setup_cfg)
            if 'egginfo' in configuration.sections:
                return SetupLoader(path=path)
            logger.debug("Missing zeam package configuration in %s" % setup_cfg)
        return None

    def install(self, release, path):
        pass

