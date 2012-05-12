
import os
import tarfile
import zipfile

from zeam.setup.base.recipe.utils import Paths


class ZipArchive(object):
    """Manage an zip archive.
    """

    def __init__(self, filename, mode):
        self.filename = filename
        self.format = os.path.splitext(self.filename)[-1]
        self._zip = zipfile.ZipFile(filename, mode)

    def add(self, filename, dest_filename):
        self._zip.write(filename, dest_filename)

    def extract(self, destination):
        filenames = Paths(verify=False)
        if self.format == '.egg':
            # Eggs are not in a directory for themselves...
            # Add a directory
            destination = os.path.join(
                destination,
                os.path.splitext(os.path.basename(self.filename))[0])

        for filename in self._zip.namelist():
            target_filename = os.path.join(destination, filename)
            target_info = self._zip.getinfo(filename)

            # ZIP specs uses / as path separator
            is_dir = (filename[-1] == '/' or
                      target_info.external_attr & 0x10 == 0x10)
            if not is_dir:
                # Extract the file if it is not a folder
                target_path = os.path.dirname(target_filename)
                if not os.path.exists(target_path):
                    os.makedirs(target_path)

                output = open(target_filename, 'wb')
                output.write(self._zip.read(filename))
                output.close()
            else:
                filename = filename.rstrip('/')
                if not os.path.exists(target_filename):
                    os.makedirs(target_filename)

            filenames.add(filename, directory=is_dir)
        return filenames

    def close(self):
        self._zip.close()


class TarArchive(object):
    """Manage a tar archive.
    """
    _format = ''

    def __init__(self, filename, mode):
        self.filename = filename
        self._tar = tarfile.open(filename, mode + self._format)

    def add(self, filename, dest_filename):
        self._tar.add(filename, dest_filename, False)

    def extract(self, destination):
        filenames = Paths(verify=False)
        for entry in self._tar:
            self._tar.extract(entry, destination)
            filename = entry.name
            if filename.startswith('./'):
                filename = filename[2:]
            filenames.add(filename, directory=entry.isdir())
        return filenames

    def close(self):
        self._tar.close()


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


def open_archive(path, mode):
    for key in ARCHIVE_MANAGER.keys():
        if path.endswith(key):
            return ARCHIVE_MANAGER[key](path, mode)
    return None
