
import os

from monteur.vcs.vcs import VCS, VCSFactory
from monteur.vcs.error import VCSError


class FileSystem(VCS):
    """VCS VCS: no VCS, just do a symlink to the sources.
    """

    def __init__(self, checkout, options=[]):
        super(FileSystem, self).__init__(checkout, options=options)
        if not os.path.isabs(self.checkout.uri):
            self.checkout.uri = os.path.normpath(
                os.path.join(
                    self.checkout.defined_directory,
                    self.checkout.uri))

    def fetch(self):
        if not os.path.exists(self.checkout.directory):
            os.symlink(self.checkout.uri, self.checkout.directory)

    update = fetch

    def verify(self):
        if os.path.islink(self.checkout.directory):
            current = os.path.abspath(
                os.readlink(self.checkout.directory))
            if self.checkout.uri != current:
                return False
        return True

    def switch(self):
        try:
            os.remove(self.checkout.directory)
            os.symlink(
                os.path.abspath(self.checkout.uri),
                self.checkout.directory)
        except OSError:
            raise VCSError(
                u"Error while updating filesystem link to",
                self.checkout.uri)


class FileSystemFactory(VCSFactory):

    available = hasattr(os, 'symlink')

    def __call__(self, checkout):
        return FileSystem(checkout)
