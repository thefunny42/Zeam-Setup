
from monteur.vcs import VCSCheckout, VCS
from monteur.session import MultiCommand
from monteur.error import InstallationError


class VCSCommand(MultiCommand):
    """Manage VCS access to the current package.
    """

    def __init__(self, session):
        super(VCSCommand, self).__init__(session)
        __status__ = u"Initializing VCS checkout"
        setup = session.configuration['setup']
        self.repository = None
        self.checkout = None
        if 'repository' in setup:
            VCS.initialize()
            option = setup['repository']
            directory = setup['prefix_directory'].as_text()
            name = 'setup'
            if 'egginfo' in session.configuration:
                egginfo = session.configuration['egginfo']
                if 'name' in egginfo:
                    name = egginfo['name']
            self.repository = option.as_words()
            self.checkout = VCSCheckout(
                name, option, self.repository, directory=directory)

    def do_update(self, args):
        """Update the current package to the latest version.
        """
        if self.checkout is not None:
            vcs = VCS(self.checkout)
            if vcs.inspect(checkout=False, update=True):
                vcs.install()
                self.session.need_reconfigure()
        else:
            raise InstallationError(
                u"No repository is defined for the working environment.")
        return False


    COMMANDS = MultiCommand.COMMANDS.copy()
    COMMANDS.update({
        'update': do_update,
        None: do_update})
