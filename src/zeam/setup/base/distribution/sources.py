
import os
import logging
import tempfile
import shutil
import py_compile

from zeam.setup.base.archives import ARCHIVE_MANAGER
from zeam.setup.base.configuration import Configuration
from zeam.setup.base.distribution import unsetuptoolize
from zeam.setup.base.distribution.release import Release
from zeam.setup.base.egginfo.read import read_pkg_entry_points
from zeam.setup.base.egginfo.read import read_pkg_info, read_pkg_requires
from zeam.setup.base.egginfo.write import write_egg_info
from zeam.setup.base.error import PackageError
from zeam.setup.base.version import Requirements

logger = logging.getLogger('zeam.setup')


def get_egg_metadata_directory(directory, name):
    return os.path.join(directory, 'EGG-INFO')


def get_source_metadata_directory(directory, name):
    return os.path.join(directory, name + '.egg-info')


METADATA_DIRECTORIES = {
    'egg': get_egg_metadata_directory,}


def get_metadata_directory(format, directory, name):
    """Return the directory that should contain the metadata depending
    of the egg format.
    """
    return METADATA_DIRECTORIES.get(format, get_source_metadata_directory)(
        directory, name)

def compile_py_files(source_dir):
    """Compile if possible all Python files.
    """
    for source_file in os.listdir(source_dir):
        source_path = os.path.join(source_dir, source_file)
        if source_path.endswith('.py') and os.path.isfile(source_path):
            py_compile.compile(source_path)
        elif os.path.isdir(source_path):
            compile_py_files(source_path)


def find_packages(source_dir):
    """Return a list of package contained in the given directory.
    """
    for possible_package in os.listdir(source_dir):
        possible_path = os.path.join(source_dir, possible_package)
        if (os.path.isfile(os.path.join(possible_path, '__init__.py')) or
            os.path.isfile(os.path.join(possible_path, '__init__.pyc'))):
            yield possible_package


def install_py_packages(target_dir, source_dir, packages):
    """Install Python packages from source_dir into target_dir.
    """
    for package in packages:
        target_package_dir = os.path.join(target_dir, package)
        if os.path.isdir(target_package_dir):
            shutil.rmtree(target_package_dir)
        shutil.copytree(
            os.path.join(source_dir, package), target_package_dir)
        compile_py_files(target_package_dir)


class UninstalledRelease(Release):
    """A release that you can install.
    """

    def __init__(self, source, name, version, format, url,
                 pyversion=None, platform=None):
        super(UninstalledRelease, self).__init__(
            name, version, pyversion=pyversion, platform=platform)
        self.source = source
        self.format = format
        self.url = url
        self.__installed = False

    def get_install_base_directory(self):
        name = '-'.join((self.name, str(self.version), 'py%s' % self.pyversion))
        return name + '.egg'

    def install(self, directory, interpretor, install_missing, archive=None):
        if self.__installed:
            raise PackageError(u"%s already installed at %s" % (
                    self.name, self.path))
        interpretor_pyversion = interpretor.get_pyversion()
        if not self.pyversion:
            self.pyversion = interpretor_pyversion
        elif self.pyversion != interpretor_pyversion:
            raise PackageError(
                u"Trying to install package %s for %s in Python version %s" % (
                    self.name, self.pyversion, interpretor_pyversion))
        if archive is None:
            archive = self.url
        factory = ARCHIVE_MANAGER.get(self.format, None)
        if factory is None:
            raise PackageError(
                u"Don't know how to read package file %s, " \
                u"unknown format %s." % (archive, self.format))
        extractor = factory(archive, 'r')
        build_dir = tempfile.mkdtemp('zeam.setup')
        extractor.extract(build_dir)

        # Archive name without extension, paying attention to .tar.gz
        # (so can't use os.path.splitext)
        source_location = os.path.basename(archive)[:-(len(self.format)+1)]
        source_location = os.path.join(build_dir, source_location)
        if not os.path.isdir(source_location):
            raise PackageError(u"Cannot introspect archive content for %s" % (
                    archive,))

        # XXX: Don't think the next try except is usefull. Maybe for
        # lower/upper case issues
        try:
            metadata = read_pkg_info(source_location)
            # Metadata package should always be about the same package
            if self.name != metadata['name']:
                logger.error("Package name %s different in metadata (%s)" % (
                        self.name, metadata['name']))
            self.name = metadata['name']
        except PackageError:
            logger.info("Missing PKG-INFO in root of package")

        source_dir = source_location
        metadata_dir = get_metadata_directory(
            self.format, source_location, self.name)
        if not os.path.isdir(metadata_dir):
            logger.info(u"Missing package metadata for package %s at %s" % (
                    self.name, metadata_dir))
            # We must have a setuptool package. Extract information if possible
            config_source = interpretor.execute(
                unsetuptoolize, '-d', source_location)
            if not config_source:
                logger.error(
                    u"Missing setuptools configuration for package %s, "
                    u"giving up" % self.name)
                return None
            # Read extracted configuration
            config = Configuration.read_lines(
                config_source.splitlines, source_location)
            setuptool_config = config['setuptools']
            # Look for requirements
            if 'install_requires' in setuptool_config:
                self.requirements = Requirements.parse(
                    setuptool_config['install_requires'].as_list())
            # Look for source directory
            if 'package_dir' in setuptool_config:
                package_config = config[
                    setuptool_config['package_dir'].as_text()]
                if '_' in package_config:
                    source_dir = os.path.join(
                        source_location, package_config['_'].as_text())
            if 'license' in setuptool_config:
                self.license = setuptool_config['license'].as_text()
            if 'author' in setuptool_config:
                self.author = setuptool_config['author'].as_text()
            if 'autor_email' in setuptool_config:
                self.author_email = setuptool_config['author_email'].as_text()
        else:
            self.entry_points = read_pkg_entry_points(metadata_dir)
            self.requirements, self.extras = read_pkg_requires(metadata_dir)
        for requirement in self.requirements:
            install_missing(requirement)

        self.path = os.path.join(directory, self.get_install_base_directory())
        install_py_packages(self.path, source_dir, find_packages(source_dir))
        write_egg_info(self)
        shutil.rmtree(build_dir)
        self.__installed = True
        return self


class UndownloadedRelease(UninstalledRelease):
    """A release that you can download.
    """

    def install(self, directory, interpretor, install_missing):
        archive = self.source.downloader.download(self.url)
        return super(UndownloadedRelease, self).install(
            directory, interpretor, install_missing, archive)

