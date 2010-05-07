
import tarfile
import zipfile


class ZipArchive(object):
    """Manage an zip archive.
    """

    def __init__(self, filename, mode):
        self.filename = filename
        self.__handle = zipfile.ZipFile(filename, mode)

    def add(self, filename, dest_filename):
        self.__handle.write(filename, dest_filename)

    def extract(self, destination):
        for filename in self.__handle.namelist():
            target_path = os.path.join(destination, filename)
            output = open(target_path, 'wb')
            output.write(self.__handle.read(filename))
            output.close()

    def close(self):
        self.__handle.close()


class TarArchive(object):
    """Manage a tar archive.
    """

    _format = ''

    def __init__(self, filename, mode):
        self.filename = filename
        self.__handle = tarfile.open(filename, mode + self._format)

    def add(self, filename, dest_filename):
        self.__handle.add(filename, dest_filename, False)

    def extract(self, destination):
        for entry in self.__handle:
            self.__handle.extract(entry, destination)

    def close(self):
        self.__handle.close()


class TarGzArchive(TarArchive):
    """Manage a tar.gz archive.
    """

    _format = ':gz'


class TarBz2Archive(TarArchive):
    """Manage a tar.bz2 archive.
    """

    _format = ':bz2'


ARCHIVE_MANAGER = {
    'egg': ZipArchive,
    'zip': ZipArchive,
    'tar': TarArchive,
    'tgz': TarGzArchive,
    'tar.gz': TarGzArchive,
    'tar.bz2': TarBz2Archive,}

