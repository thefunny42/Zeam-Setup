
import os

from zeam.setup.base.archives import ARCHIVE_MANAGER
from zeam.setup.base.distribution import Release
from zeam.setup.base.error import PackageError


class UninstalledRelease(Release):
    """A release that you can install.
    """

    def __init__(self, source, name, version, format, url):
        super(UninstalledRelease, self).__init__(name, version)
        self.source = source
        self.format = format
        self.url = url

    def install(self, directory, archive=None):
        if archive is None:
            archive = self.url
        factory = ARCHIVE_MANAGER.get(self.format, None)
        if factory is None:
            raise PackageError, u"Don't know how to read package file %s, " \
                u"unknown format %s." % (archive, self.format)
        extractor = factory(archive, 'r')
        extractor.extract(directory)
        # Archive name without extension, paying attention to .tar.gz
        # (so can't use os.path.splitext)
        source_location = os.path.basename(archive)[:-(len(self.format)+1)]
        source_location = os.path.join(directory, source_location)
        if not os.path.isdir(source_location):
            raise PackageError, u"Cannot introspect archive content"
        
        return None


class UndownloadedRelease(UninstalledRelease):
    """A release that you can download.
    """

    def install(self, directory):
        archive = self.source.downloader.download(self.url)
        return super(UndownloadedRelease, self).install(directory, archive)

