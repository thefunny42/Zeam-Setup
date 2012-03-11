
import logging
import sys

from zeam.setup.base.distribution.workingset import working_set

logger = logging.getLogger('zeam.setup')


class EggInfo(object):
    """Command used to create egg information for a package.
    """

    def __init__(self, session):
        self.session = session

    def run(self):
        # This line load the package to return it (and write its EGG-INFO).
        self.session.configuration.utilities.package
        self.session.events.one('transaction', self.session.reconfigure)
        return False


class Installed(object):
    """Command used to list installed software.
    """

    def __init__(self, session):
        pass

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
