
import os
import tempfile
import shutil
import shlex
import logging

from monteur.archives import open_archive
from monteur.download import DownloadManager
from monteur.recipe.recipe import Recipe
from monteur.error import ConfigurationError, InstallationError
from monteur.utils import create_directory, relative_uri
from monteur.recipe.utils import MultiTask, Paths


logger = logging.getLogger('monteur')


def parse_files(options, name):
    """Help to read filenames and put them back where they where
    defined.
    """
    if name not in options:
        return []
    value = options[name]
    origin = value.get_cfg_directory()

    def parse_line(line):
        options = shlex.split(line)
        mapping = []
        for info in options[1:]:
            directories = info.split(':')
            if len(directories) != 2:
                raise ConfigurationError(
                    value.location, u"Invalid directory definition", info)
            mapping.append(directories)
        return relative_uri(origin, options[0], True), mapping

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
        self._do = MultiTask(options, 'download')

    def install_file(self, source_path, destination_path, directory):
        """Install a folder or a file to a installation one.
        """
        if destination_path in self.status.installed_paths:
            self.status.paths.add(destination_path, directory=directory)
            return

        if directory:
            if os.path.exists(destination_path):
                if not os.path.isdir(destination_path):
                    raise InstallationError(
                        u"Error target directory already exists",
                        destination_path)
            else:
                create_directory(destination_path, quiet=True)
        else:
            if os.path.exists(destination_path):
                raise InstallationError(
                    u"Error target file already exists",
                    destination_path)
            if not os.path.exists(source_path):
                raise InstallationError(
                    u"Error missing directory or file in source",
                    source_path)
            parent_path = os.path.dirname(destination_path)
            if not os.path.exists(parent_path):
                create_directory(parent_path, quiet=True)
            shutil.copy2(source_path, destination_path)
        self.status.paths.add(destination_path, directory=directory, added=True)

    def install_files(self, origin_path, target_path, files):
        """Install a set of files.
        """
        for path, data in files.items():
            source_path = os.path.join(origin_path, data['original'])
            destination_path = target_path
            if path:
                destination_path = os.path.join(destination_path, path)
            self.install_file(source_path, destination_path, data['directory'])

    def preinstall(self):
        __status__ = u"Download files."
        download = lambda (uri, parts): (self.downloader(uri), parts)
        self.files = self._do(download, self.files + self.urls)

    def install(self):
        __status__ = u"Install files."
        target_directory = self.directory
        for filename, parts in self.files:
            archive = open_archive(filename, 'r')
            if archive is not None:
                extract_path = tempfile.mkdtemp('monteur.archive')
                extracted = archive.extract(extract_path)
                try:
                    if parts:
                        for source_part, destination_part in parts:
                            files = extracted.as_dict(
                                prefixes={source_part: destination_part})
                            if not files:
                                raise ConfigurationError(
                                    u'Missing wanted path in archive')
                            self.install_files(
                                extract_path,
                                target_directory,
                                files)
                    else:
                        self.install_files(
                            extract_path,
                            target_directory,
                            extracted.as_dict())
                finally:
                    shutil.rmtree(extract_path)
            else:
                if not os.path.isdir(filename):
                    raise ConfigurationError(
                        u"Cannot not directly install files, only directories",
                        filename)
                files = Paths(verify=False)
                files.listdir(filename)
                if parts:
                    for source_part, destination_part in parts:
                        part_files = files.as_dict(
                            prefixes={source_part: destination_part})
                        if not part_files:
                            raise ConfigurationError(
                                u'Missing wanted path in archive')
                        self.install_files(
                            filename,
                            target_directory,
                            part_files)
                else:
                    target_path = os.path.join(
                        target_directory, os.path.basename(filename))
                    self.install_files(
                        target_path,
                        target_directory,
                        files)

    def uninstall(self):
        __status__ = u"Uninstalling files."
        for filename in self.status.installed_paths.as_list():
            if os.path.exists(filename):
                if os.path.isdir(filename):
                    shutil.rmtree(filename)
                else:
                    os.remove(filename)
            else:
                raise InstallationError(
                    u"Missing files while uninstalling", filename)
