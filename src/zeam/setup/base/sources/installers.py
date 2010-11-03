
import os
import logging
import tempfile
import shutil
import py_compile

from zeam.setup.base.egginfo.loader import EggLoaderFactory
from zeam.setup.base.setuptools.loader import SetuptoolsLoaderFactory
from zeam.setup.base.distribution.loader import SetupLoaderFactory
from zeam.setup.base.archives import ARCHIVE_MANAGER
from zeam.setup.base.distribution.release import Release
from zeam.setup.base.egginfo.write import write_egg_info
from zeam.setup.base.error import PackageError

logger = logging.getLogger('zeam.setup')

LOADERS = [EggLoaderFactory(),
           SetuptoolsLoaderFactory(),
           SetupLoaderFactory()]


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
        logger.info("Install Python files for %s into %s" % (
                package, target_package_dir))
        if os.path.isdir(target_package_dir):
            logger.debug("Cleaning installation directory %s" % (
                    target_package_dir))
            shutil.rmtree(target_package_dir)
        shutil.copytree(
            os.path.join(source_dir, package), target_package_dir)
        compile_py_files(target_package_dir)


class PackageInstaller(object):
    """Install an already installed package: load informations and
    install dependencies.
    """

    def __init__(self, source, **informations):
        self.source = source
        assert 'name' in informations
        informations.setdefault('version', None)
        self.informations = informations

    def __getattr__(self, key):
        if key in self.informations:
            return self.informations[key]
        raise AttributeError(key)

    # XXX Following three methods need review
    def __lt__(self, other):
        return self.version < other.version

    def __gt__(self, other):
        return self.version > other.version

    def __eq__(self, other):
        return self.version == other.version

    def load_metadata(self, distribution, path, interpretor):
        for factory in LOADERS:
            loader = factory.available(path)
            if loader is not None:
                assert loader.load(distribution, interpretor) is distribution
                break
        else:
            raise PackageError(
                u"Unknow package type at %s" % (path))

    def install(self, path, interpretor, install_dependencies):
        distribution = Release(**self.informations)
        self.load_metadata(distribution, distribution.path, interpretor)
        install_dependencies(distribution)
        return distribution


class UninstalledPackageInstaller(PackageInstaller):
    """A release that you can install.
    """

    def get_install_base_directory(self):
        name = self.informations['name']
        version = self.informations['version']
        pyversion = self.informations['pyversion']
        return '-'.join((name, str(version), 'py%s' % pyversion)) + '.egg'

    def install(self, path, interpretor, install_dependencies, archive=None):
        pyversion = self.informations['pyversion']
        interpretor_pyversion = interpretor.get_pyversion()
        if pyversion is None:
            pyversion = interpretor_pyversion
        elif pyversion != interpretor_pyversion:
            raise PackageError(
                u"Trying to install package %s for %s in Python version %s" % (
                    self.informations['name'],
                    pyversion,
                    interpretor_pyversion))
        self.informations['pyversion'] = pyversion

        if archive is None:
            archive = self.informations['url']

        format = self.informations['format']
        factory = ARCHIVE_MANAGER.get(format, None)
        if factory is None:
            raise PackageError(
                u"Don't know how to read package file %s, " \
                u"unknown format %s." % (archive, format))
        extractor = factory(archive, 'r')
        build_dir = tempfile.mkdtemp('zeam.setup')
        extractor.extract(build_dir)

        # Archive name without extension, paying attention to .tar.gz
        # (so can't use os.path.splitext)
        source_location = os.path.basename(archive)[:-(len(format)+1)]
        source_location = os.path.join(build_dir, source_location)
        if not os.path.isdir(source_location):
            raise PackageError(u"Cannot introspect archive content for %s" % (
                    archive,))
        self.informations['path'] = source_location

        # Load project information
        distribution = super(UninstalledPackageInstaller, self).install(
            path, interpretor, install_dependencies)

        # Install files
        source_dir = distribution.path
        install_path = os.path.join(path, self.get_install_base_directory())
        install_py_packages(install_path, source_dir, find_packages(source_dir))
        shutil.rmtree(build_dir)

        # Package path is now the installed path
        distribution.path = install_path
        distribution.package_path = install_path

        write_egg_info(distribution)
        return distribution


class UndownloadedPackageInstaller(UninstalledPackageInstaller):
    """A release that you can download.
    """

    def install(self, path, interpretor, install_dependencies):
        archive = self.source.downloader.download(self.url)
        return super(UndownloadedPackageInstaller, self).install(
            path, interpretor, install_dependencies, archive)

