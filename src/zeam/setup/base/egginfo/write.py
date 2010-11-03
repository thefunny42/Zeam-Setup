
import logging
import os

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


def write_requires(path, package):
    requirements = package.requirements
    if requirements:
        file = open(os.path.join(path, 'requires.txt'), 'w')
        for requirement in requirements:
            file.write(str(requirement) + '\n')
        for extra, requirements in package.extras.items():
            file.write('\n\n[%s]\n' % extra)
            for requirement in requirements:
                file.write(str(requirement) + '\n')
        file.close()

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
                                     write_entry_points,
                                     write_requires]):
    logger.info('Writing EGG-INFO in %s for %s' % (
            package.path, package.name))
    path = os.path.join(package.path, 'EGG-INFO')
    create_directory(path)

    for writer in writers:
        writer(path, package)
