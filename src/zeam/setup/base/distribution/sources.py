
from zeam.setup.base.distribution import Release


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
        return None


class UndownloadedRelease(UninstalledRelease):
    """A release that you can download.
    """

    def install(self, directory):
        archive = self.source.downloader.download(self.url)
        return super(UndownloadedRelease, self).install(directory, archive)

