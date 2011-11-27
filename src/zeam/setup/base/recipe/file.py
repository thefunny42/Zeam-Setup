
import os
import tempfile
import shutil
import shlex

from zeam.setup.base.archives import open_archive
from zeam.setup.base.download import DownloadManager
from zeam.setup.base.python import PythonInterpreter
from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.error import InstallationError, ConfigurationError
from zeam.setup.base.utils import create_directory


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
        current_parent_path = os.path.dirname(target_path)
        if not os.path.exists(current_parent_path):
            create_directory(current_parent_path)
        source_path = os.path.join(extract_path, source_part)
        if not os.path.exists(source_path):
            raise ConfigurationError(
                u"Error missing directory in archive", source_path)
        shutil.move(source_path, current_path)
        installed_paths.append(current_path)
    return installed_paths


class File(Recipe):
    """Download a list of files and archives in a folder.
    """

    def __init__(self, configuration):
        super(File, self).__init__(configuration)
        self.urls = configuration['urls'].as_list()
        self.post_python_commands = configuration.get(
            'post_python_commands', '').as_list()
        self.interpreter = PythonInterpreter.detect(
            configuration.configuration['setup']['python_executable'].as_text())
        self.target = configuration['directory'].as_text()
        download_path = configuration.get(
            'download_directory',
            '${setup:prefix_directory}/download').as_text()
        create_directory(download_path)
        self.downloader = DownloadManager(download_path)

    def install(self):
        __status__ = u"Download files."
        downloaded_files = []
        for url_info in self.urls:
            url_parts = shlex.split(url_info)
            path = self.downloader(url_parts[0])
            archive = open_archive(path, 'r')
            if archive is not None:
                if len(url_parts) > 1:
                    extract_path = tempfile.mkdtemp('zeam.setup.archive')
                    archive.extract(extract_path)
                    downloaded_files.extend(
                        move_archive_folders(
                            extract_path, self.target, url_parts[1:]))
                    shutil.rmtree(extract_path)
                else:
                    create_directory(self.target)
                    archive.extract(self.target)
            else:
                shutil.copy2(path, self.target)
            downloaded_files.append(self.target)
        for command in self.post_python_commands:
            stdout, stdin, code = self.interpreter.execute_external(
                *shlex.split(command), path=self.target)
            if code:
                raise InstallationError(
                    u"Post extraction command failed", '\n' + (stdout or stdin))
        return downloaded_files
