
import os

from zeam.setup.base.archives import ARCHIVE_MANAGER
from zeam.setup.base.distribution.release import Release
from zeam.setup.base.distribution.egg import read_pkg_info, read_pkg_requires
from zeam.setup.base.error import PackageError


def get_egg_metadata_directory(directory, name):
    return os.path.join(directory, 'EGG-INFO')


def get_source_metadata_directory(directory, name):
    return os.path.join(directory, name + '.egg-info')


METADATA_DIRECTORIES = {
    'egg': get_egg_metadata_directory,}


def get_metadata_directory(format, directory, name):
    return METADATA_DIRECTORIES.get(format, get_source_metadata_directory)(
        directory, name)


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

    def install(self, directory, install_missing, archive=None):
        if archive is None:
            archive = self.url
        factory = ARCHIVE_MANAGER.get(self.format, None)
        if factory is None:
            raise PackageError(
                u"Don't know how to read package file %s, " \
                u"unknown format %s." % (archive, self.format))
        extractor = factory(archive, 'r')
        extractor.extract(directory)

        # Archive name without extension, paying attention to .tar.gz
        # (so can't use os.path.splitext)
        source_location = os.path.basename(archive)[:-(len(self.format)+1)]
        source_location = os.path.join(directory, source_location)
        if not os.path.isdir(source_location):
            raise PackageError(u"Cannot introspect archive content")

        # XXX: Don't think the next try except is usefull. Maybe for
        # lower/upper case issues
        try:
            metadata = read_pkg_info(source_location)
            # Metadata package should always be about the same package
            if self.name != metadata['name']:
                print "Package name different in metadata"
            self.name == metadata['name']
        except PackageError:
            print "Missing PKG-INFO in root of package"

        metadata_dir = get_metadata_directory(
            self.format, source_location, self.name)
        if not os.path.isdir(metadata_dir):
            print u"Missing package metadata for %s at %s" % (
                    self.name, metadata_dir)

        self.requirements, self.extras = read_pkg_requires(metadata_dir)
        for requirement in self.requirements:
            install_missing(requirement)
        return None


class UndownloadedRelease(UninstalledRelease):
    """A release that you can download.
    """

    def install(self, directory, install_missing):
        archive = self.source.downloader.download(self.url)
        return super(UndownloadedRelease, self).install(
            directory, install_missing, archive)

