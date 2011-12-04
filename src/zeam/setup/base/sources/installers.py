
import os
import logging
import tempfile
import shutil

from zeam.setup.base.archives import ARCHIVE_MANAGER
from zeam.setup.base.distribution.release import Release, load_metadata
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


class ExtractedPackageInstaller(PackageInstaller):
    """An extracted release that you can install.
    """

    def install(self, path, interpretor, install_dependencies):
        # Load project information
        distribution, loader = super(ExtractedPackageInstaller, self).install(
            path, interpretor, install_dependencies)

        # Install files
        install_path = os.path.join(
            path, distribution.get_egg_directory(interpretor))
        loader.install(install_path)

        # Package path is now the installed path
        distribution.path = install_path
        distribution.package_path = install_path
        return distribution, loader


class UninstalledPackageInstaller(ExtractedPackageInstaller):
    """A release that you can extract from an archive and install.
    """

    def install(self, path, interpretor, install_dependencies, archive=None):
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
        source_path = os.path.basename(archive)[:-(len(format)+1)]
        source_path = os.path.join(build_dir, source_path)
        if not os.path.isdir(source_path):
            logger.debug(
                u"Non-standard archive for %s" % self.informations['name'])
            # Ok the folder has the same name than the archive. Try to
            # see if there is only one folder in the archive, ignore
            # what starts with .
            source_path = None
            candidates_entries = filter(
                lambda s: s and s[0] != '.', os.listdir(build_dir))
            if len(candidates_entries) == 1:
                candidate_path = os.path.join(build_dir, candidates_entries[0])
                if os.path.isdir(candidate_path):
                    # If there is only one directory in the archive use it.
                    source_path = candidate_path
            if source_path is None:
                raise PackageError(
                    u"Cannot introspect archive content for %s" % (archive,))
        self.informations['path'] = source_path

        # Load project information
        distribution, loader = super(UninstalledPackageInstaller, self).install(
            path, interpretor, install_dependencies)

        # Clean build directory
        shutil.rmtree(build_dir)

        return distribution, loader


class UndownloadedPackageInstaller(UninstalledPackageInstaller):
    """A release that you can download.
    """

    def install(self, path, interpretor, install_dependencies):
        archive = self.source.downloader.download(self.url)
        return super(UndownloadedPackageInstaller, self).install(
            path, interpretor, install_dependencies, archive)

