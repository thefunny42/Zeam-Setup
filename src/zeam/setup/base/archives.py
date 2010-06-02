
import os
import tarfile
import zipfile


class ZipArchive(object):
    """Manage an zip archive.
    """

    def __init__(self, filename, mode):
        self.filename = filename
        self.format = os.path.splitext(self.filename)[-1]
        self.__handle = zipfile.ZipFile(filename, mode)

    def add(self, filename, dest_filename):
        self.__handle.write(filename, dest_filename)

    def extract(self, destination):
        if self.format == '.egg':
            # Eggs are not in a directory for themselves...
            # Add a directory
            destination = os.path.join(
                destination,
                os.path.splitext(os.path.basename(self.filename))[0])

        for filename in self.__handle.namelist():
            target_filename = os.path.join(destination, filename)

            # Create directory for target_filename
            target_path = os.path.dirname(target_filename)
            if not os.path.exists(target_path):
                os.makedirs(target_path)

            # Extract the file
            output = open(target_filename, 'wb')
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

