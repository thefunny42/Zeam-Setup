
import os
import logging
import tempfile
import shutil

from zeam.setup.base.archives import ARCHIVE_MANAGER
from zeam.setup.base.distribution.release import Release, load_metadata
from zeam.setup.base.egginfo.write import write_egg_info
from zeam.setup.base.error import PackageError

logger = logging.getLogger('zeam.setup')


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

    def install(self, path, interpretor, install_dependencies):
        distribution = Release(**self.informations)
        loader = load_metadata(distribution, distribution.path, interpretor)
        install_dependencies(distribution)
        return distribution, loader


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
        distribution, loader = super(UninstalledPackageInstaller, self).install(
            path, interpretor, install_dependencies)

        # Install files
        install_path = os.path.join(path, self.get_install_base_directory())
        loader.install(install_path)

        shutil.rmtree(build_dir)

        # Package path is now the installed path
        distribution.path = install_path
        distribution.package_path = install_path

        write_egg_info(distribution)
        return distribution, loader


class UndownloadedPackageInstaller(UninstalledPackageInstaller):
    """A release that you can download.
    """

    def install(self, path, interpretor, install_dependencies):
        archive = self.source.downloader.download(self.url)
        return super(UndownloadedPackageInstaller, self).install(
            path, interpretor, install_dependencies, archive)

