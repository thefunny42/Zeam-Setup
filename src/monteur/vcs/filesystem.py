
import os

from monteur.vcs.vcs import VCS, VCSFactory
from monteur.vcs.error import VCSError


class FileSystem(VCS):
    """VCS VCS: no VCS, just do a symlink to the sources.
    """

    def __init__(self, package, options=[]):
        super(FileSystem, self).__init__(package, options=options)
        if not os.path.isabs(self.package.uri):
            self.package.uri = os.path.normpath(
                os.path.join(self.package.defined_directory, self.package.uri))

    def checkout(self):
        if not os.path.exists(self.package.directory):
            os.symlink(self.package.uri, self.package.directory)

    update = checkout

    def verify(self):
        if os.path.islink(self.package.directory):
            current = os.path.abspath(
                os.readlink(self.package.directory))
            if self.package.uri != current:
                return False
        return True

    def switch(self):
        try:
            os.remove(self.package.directory)
            os.symlink(
                os.path.abspath(self.package.uri),
                self.package.directory)
        except OSError:
            raise VCSError(
                u"Error while updating filesystem link to",
                self.package.uri)


class FileSystemFactory(VCSFactory):

    available = hasattr(os, 'symlink')

    def __call__(self, package):
        return FileSystem(package)
