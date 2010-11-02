
import logging
import sys

from zeam.setup.base.distribution.workingset import WorkingSet
from zeam.setup.base.distribution.release import DevelopmentRelease
from zeam.setup.base.egginfo.write import write_egg_info

logger = logging.getLogger('zeam.setup')


class EggInfo(object):
    """Command used to create egg information for a package.
    """

    def __init__(self, configuration):
        self.configuration = configuration
        self.package = DevelopmentRelease(config=configuration)

    def run(self):
        write_egg_info(self.package)


class Installed(object):
    """Command used to list installed software.
    """

    def __init__(self, configuration):
        self.configuration = configuration

    def run(self):
        # It's not errors, but the moment we use the log facily to
        # report information.
        installed = WorkingSet().installed.items()
        installed.sort(key=lambda (k,v):k)
        logger.error("Running Python %s" % sys.version)
        logger.error("Installed packages:")
        for name, package in installed:
            logger.error("- %s, version %s" % (package.name, package.version))
            if package.summary:
                logger.warning("  Description:")
                logger.warning("  %s" % package.summary)
            requires = package.requirements.requirements
            if requires:
                logger.info("  Requires:")
                for dependency in requires:
                    logger.info("  + %s" % dependency)

