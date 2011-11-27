
import os
import tempfile
import shutil
import shlex

from zeam.setup.base.archives import open_archive
from zeam.setup.base.download import DownloadManager
from zeam.setup.base.python import PythonInterpreter
from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.error import InstallationError
from zeam.setup.base.utils import create_directory


class Files(Recipe):
    """Download a list of files and archives in a folder.
    """

    def __init__(self, configuration):
        super(Files, self).__init__(configuration)
        self.urls = configuration['urls'].as_list()
        self.post_python_commands = configuration.get(
            'post_python_commands', '').as_list()
        self.interpreter = PythonInterpreter.detect(
            configuration.configuration['setup']['python_executable'].as_text())
        self.target = configuration['target_directory'].as_text()
        self.target_only = configuration.get('target_only', '').as_text()
        download_path = configuration.get(
            'download_directory',
            '${setup:prefix_directory}/download').as_text()
        create_directory(download_path)
        self.downloader = DownloadManager(download_path)

    def install(self):
        __status__ = u"Download files."
        downloaded_files = []
        for url in self.urls:
            path = self.downloader.download(url)
            archive = open_archive(path, 'r')
            if archive is not None:
                if self.target_only:
                    extract_path = tempfile.mkdtemp('zeam.setup.archive')
                    try:
                        archive.extract(extract_path)
                        shutil.move(
                            os.path.join(extract_path, self.target_only),
                            self.target)
                    finally:
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
