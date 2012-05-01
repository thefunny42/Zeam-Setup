
import logging
import os

from zeam.setup.base.archives import ARCHIVE_MANAGER
from zeam.setup.base.distribution.manifest import parse_manifest
from zeam.setup.base.error import PackageError
from zeam.setup.base.recipe.utils import Paths

logger = logging.getLogger('zeam.setup')

DEFAULT_MANIFEST = os.path.join(os.path.dirname(__file__), 'MANIFEST.in')


def get_archive_manager(config, filename, mode):
    """Create an archive manager for correct selected format selected
    in the configuration.
    """
    format = config['setup']['archive_format'].as_text()
    if format not in ARCHIVE_MANAGER.keys():
        raise PackageError(u"Unknow package format %s" % format)
    return ARCHIVE_MANAGER[format]('.'.join((filename, format,),), mode)


class SourceDistribution(object):
    """Create a source distribution of the package
    """

    def __init__(self, session):
        self.configuration = session.configuration
        self.package = self.configuration.utilities.package
        self.prefix = self.configuration['setup']['prefix_directory'].as_text()

    def manifest(self):
        manifest_name = DEFAULT_MANIFEST
        egginfo = self.configuration['egginfo']
        if 'manifest' in egginfo:
            manifest_name = egginfo['manifest'].as_file()

        files = Paths(verify=False)
        files.listdir(self.prefix)
        return files.as_manifest(*parse_manifest(manifest_name))

    def run(self):
        basename = '%s-%s' % (self.package.name, self.package.version)
        archive = get_archive_manager(self.configuration, basename, 'w')
        logger.info(u'Creating %s.', archive.filename)
        for filename, info in self.manifest():
            logger.debug(u'Adding file %s.', filename)
            archive.add(
                os.path.join(info['full']),
                os.path.join(basename, filename))
        archive.close()
        return False
