
import logging
import os
import sys

from zeam.setup.base.distribution import DevelopmentRelease
from zeam.setup.base.utils import create_directory

logger = logging.getLogger('zeam.setup')


def write_pkg_info(path, package):
    pkg_info = open(os.path.join(path, 'PKG-INFO'), 'w')
    pkg_info.write('Metadata-Version: 1.0\n')
    pkg_info.write('Name: %s\n' % package.name)
    pkg_info.write('Version: %s\n' % package.version)

    def write_options(key, value):
        if value:
            pkg_info.write('%s: %s\n' % (key, value))

    write_options('Summary', package.summary)
    write_options('Author', package.author)
    write_options('Author-email', package.author_email)
    write_options('License', package.license)
    pkg_info.write('Platform: %s\n' % (package.platform or 'UNKNOWN'))
    pkg_info.close()


def write_missing_setuptool_files(path, package):
    for filename in ['dependency_links.txt', 'not-zip-safe']:
        file = open(os.path.join(path, filename), 'w')
        file.write('\n')
        file.close()


def write_entry_points(path, package):
    if package.entry_points:
        formatted_points = ''
        for section, entries in package.entry_points.items():
            formatted_points += '[%s]\n' % section
            for name, module in entries.items():
                formatted_points += '%s = %s\n' % (name, module)
            formatted_points += '\n'

        entry_points = open(os.path.join(path, 'entry_points.txt'), 'w')
        entry_points.write(formatted_points)
        entry_points.close()


def write_egg_info(package, writers=[write_pkg_info,
                                     write_missing_setuptool_files,
                                     write_entry_points]):
    logger.warning('Writing EGG-INFO in %s for %s' % (
            package.path, package.name))
    path = os.path.join(package.path, 'EGG-INFO')
    create_directory(path)

    for writer in writers:
        writer(path, package)


class EggInfo(object):
    """Command used to create egg information for a package.
    """

    writers = [write_pkg_info,
               write_missing_setuptool_files,
               write_entry_points]

    def __init__(self, config, environment):
        self.config = config
        self.environment = environment
        self.package = DevelopmentRelease(config=config)

    def run(self):
        write_egg_info(self.package, self.writers)


class Installed(object):
    """Command used to list installed software.
    """

    def __init__(self, config, environment):
        self.config = config
        self.environment = environment

    def run(self):
        # It's not errors, but the moment we use the log facily to
        # report information.
        installed = self.environment.installed.items()
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

