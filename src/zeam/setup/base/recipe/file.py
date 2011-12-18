
import os
import tempfile
import shutil
import shlex
import logging

from zeam.setup.base.archives import open_archive
from zeam.setup.base.download import DownloadManager
from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.error import ConfigurationError, InstallationError
from zeam.setup.base.utils import create_directory, relative_uri

logger = logging.getLogger('zeam.setup')


def install_data(source_path, destination_path, status, move=True):
    """Install a folder or a file to a installation one.
    """
    if destination_path in status.installed_paths:
        logger.debug(
            u"Skipping already installed directory or file %s.",
            destination_path)
        status.paths.add(destination_path, added=False)
    else:
        if os.path.exists(destination_path):
            raise InstallationError(
                u"Error target directory or file already exists",
                destination_path)
        if not os.path.exists(source_path):
            raise InstallationError(
                u"Error missing directory or file in source",
                source_path)
        parent_path = os.path.dirname(destination_path)
        if not os.path.exists(parent_path):
            create_directory(parent_path)
        logger.debug(
            u"Installing directory or file %s.",
            destination_path)
        if move:
            shutil.move(source_path, destination_path)
        else:
            shutil.copy2(source_path, destination_path)
        status.paths.add(destination_path, added=True)

def install_specified_data(origin_path, target_path, infos, status, move=True):
    """Install specified folders or files from an origin path into the
    installation path.
    """
    for info in infos:
        parts = info.split(':')
        if len(parts) != 2:
            raise ConfigurationError(u"Invalid directory definition", info)
        destination_path = target_path
        source_part, destination_part = parts
        source_path = os.path.join(origin_path, source_part)
        if destination_part:
            destination_path = os.path.join(destination_path, destination_part)
        install_data(source_path, destination_path, status, move=move)

def install_folder_data(origin_path, target_path, status, move=True):
    """Install all folder entries from an origin path into the
    installation path.
    """
    for entry in os.listdir(origin_path):
        install_data(
            os.path.join(origin_path, entry),
            os.path.join(target_path, entry),
            status,
            move=move)

def parse_files(options, name):
    """Help to read filenames and put them back where they where
    defined.
    """
    if name not in options:
        return []
    value = options[name]
    origin = value.get_cfg_directory()

    def parse_line(line):
        parts = shlex.split(line)
        return relative_uri(origin, parts[0], True), parts[1:]

    return map(parse_line, value.as_list())


class File(Recipe):
    """Download a list of files and archives in a folder.
    """

    def __init__(self, options, status):
        super(File, self).__init__(options, status)
        self.files = parse_files(options, 'files')
        self.urls = parse_files(options, 'urls')
        self.directory = options['directory'].as_text()
        download_path = options.get(
            'download_directory',
            '${setup:prefix_directory}/download').as_text()
        create_directory(download_path)
        self.downloader = DownloadManager(download_path)

    def prepare(self):
        __status__ = u"Download files."
        process = lambda (uri, parts): (self.downloader(uri), parts)
        self.files = map(process, self.files) + map(process, self.urls)

    def install(self):
        __status__ = u"Install files."
        target_directory = self.directory
        for filename, parts in self.files:
            archive = open_archive(filename, 'r')
            if archive is not None:
                extract_path = tempfile.mkdtemp('zeam.setup.archive')
                archive.extract(extract_path)
                try:
                    if parts:
                        install_specified_data(
                            extract_path,
                            target_directory,
                            parts,
                            self.status,
                            move=True)
                    else:
                        install_folder_data(
                            extract_path,
                            target_directory,
                            self.status,
                            move=True)
                finally:
                    shutil.rmtree(extract_path)
            else:
                if parts:
                    if os.path.isdir(filename):
                        install_specified_data(
                            filename,
                            target_directory,
                            parts,
                            self.status,
                            move=False)
                    else:
                        raise ConfigurationError(
                            u"Parts are defined, but is not a directory",
                            filename)
                else:
                    target_path = os.path.join(
                        target_directory, os.path.basename(filename))
                    install_data(filename, target_path, self.status, move=False)

    def uninstall(self):
        __status__ = u"Uninstalling files."
        for filename in self.status.installed_paths.as_list():
            if os.path.exists(filename):
                shutil.rmtree(filename)
            else:
                raise InstallationError(
                    u"Missing files while uninstalling", filename)
