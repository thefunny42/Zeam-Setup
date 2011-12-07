
import os
import tempfile
import shutil
import shlex

from zeam.setup.base.archives import open_archive
from zeam.setup.base.download import DownloadManager
from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.error import ConfigurationError, InstallationError
from zeam.setup.base.utils import create_directory, relative_uri


def move_archive_folders(extract_path, target_path, path_infos):
    """Move specified archive folder into the installation path.
    """
    installed_paths = []
    for path_info in path_infos:
        path_parts = path_info.split(':')
        if len(path_parts) != 2:
            raise ConfigurationError(
                u"Invalid archive directory definition", path_info)
        current_path = target_path
        source_part, target_part = path_parts
        if target_part:
            current_path = os.path.join(current_path, target_part)
        if os.path.exists(current_path):
            raise ConfigurationError(
                u"Error target directory already exists", current_path)
        current_parent_path = os.path.dirname(current_path)
        if not os.path.exists(current_parent_path):
            create_directory(current_parent_path)
        source_path = os.path.join(extract_path, source_part)
        if not os.path.exists(source_path):
            raise ConfigurationError(
                u"Error missing directory in archive", source_path)
        shutil.move(source_path, current_path)
        installed_paths.append(current_path)
    return installed_paths

def parse_line(line):
    parts = shlex.split(line)
    return parts[0], parts[1:]


class File(Recipe):
    """Download a list of files and archives in a folder.
    """

    def __init__(self, options):
        super(File, self).__init__(options)
        self.files = map(parse_line, options.get('files', '').as_list())
        self.urls = map(parse_line, options.get('urls', '').as_list())
        self.directory = options['directory'].as_text()
        download_path = options.get(
            'download_directory',
            '${setup:prefix_directory}/download').as_text()
        create_directory(download_path)
        self.downloader = DownloadManager(download_path)

    def prepare(self, status):
        __status__ = u"Download files."
        origin = self.options.get_cfg_directory()
        process = lambda (uri, parts): (
            self.downloader(relative_uri(origin, uri, True)), parts)
        self.files = map(process, self.files) + map(process, self.urls)

    def install(self, status):
        __status__ = u"Install files."
        for file, parts in self.files:
            archive = open_archive(file, 'r')
            if archive is not None:
                if parts:
                    path = tempfile.mkdtemp('zeam.setup.archive')
                    archive.extract(path)
                    status.add_paths(
                        move_archive_folders(path, self.directory, parts))
                    shutil.rmtree(path)
                else:
                    create_directory(self.directory)
                    archive.extract(self.directory)
            else:
                create_directory(self.directory)
                try:
                    shutil.copy2(file, self.directory)
                except IOError:
                    raise InstallationError(
                        u'Missing required setup file', file)
            status.add_path(self.directory)

