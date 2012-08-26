
import logging
import sys

from monteur.egginfo.write import write_egg_info
from monteur.distribution.workingset import working_set
from monteur.session import Command

logger = logging.getLogger('monteur')


class EggInfoCommand(Command):
    """Command used to create egg information for a package.
    """

    def run(self):
        # This line load the package to return it (and write its EGG-INFO).
        write_egg_info(self.session.configuration.utilities.package)
        self.session.need_reconfigure()
        return False


class InstalledCommand(Command):
    """Command used to list installed software.
    """

    def run(self):
        # It's not errors, but the moment we use the log facily to
        # report information.
        logger.error("Running Python %s" % sys.version)
        logger.error("Installed packages:")
        for package in sorted(working_set, key=lambda release: release.name):
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
