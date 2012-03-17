
import logging
import sys

from zeam.setup.base.distribution.workingset import working_set
from zeam.setup.base.session import Command

logger = logging.getLogger('zeam.setup')


class EggInfoCommand(Command):
    """Command used to create egg information for a package.
    """

    def run(self):
        # This line load the package to return it (and write its EGG-INFO).
        self.session.configuration.utilities.package
        self.session.need_reconfigure()
        return False


class InstalledCommand(Command):
    """Command used to list installed software.
    """

    def run(self):
        # It's not errors, but the moment we use the log facily to
        # report information.
        installed = working_set.installed.items()
        installed.sort(key=lambda (k,v):k)
        logger.error("Running Python %s" % sys.version)
        logger.error("Installed packages:")
        for name, package in installed:
            logger.error("- %s, version %s" % (package.name, package.version))
            if package.summary:
                logger.warning("  Description:")
                logger.warning("  %s" % package.summary)
            requires = package.requirements
            if requires:
                logger.info("  Requires:")
                for dependency in requires:
                    logger.info("  + %s" % dependency)
        return False
