
from optparse import OptionParser
import logging
import os
import socket
import sys

from monteur.session import Session
from monteur.distribution.kgs import KGS
from monteur.distribution.workingset import working_set
from monteur.distribution.release import current_package, Loaders
from monteur.error import InstallationError, logs
from monteur.recipe.commands import Installer
from monteur.utils import create_directory
from monteur.sources.sources import Sources
from monteur.egginfo.commands import EggInfoCommand

logger = logging.getLogger('monteur')


def bootstrap(session):
    """Bootstrap the configuration settings. Mainly set things like
    network_timeout, prefix_directory, python_executable.
    """
    __status__ = u"Initializing environment."
    configuration = session.configuration
    setup = configuration['setup']
    options = session.options

    # Export command line settings
    setup['verbosity'] = options.verbosity
    setup['debug'] = bool(options.debug)
    setup['offline'] = bool(options.offline)

    def set_timeout(timeout):
        logger.info(u'Setting networking timeout to %d seconds.', timeout)
        socket.setdefaulttimeout(timeout)

    # Network timeout
    if options.timeout:
        set_timeout(options.timeout)
    elif 'network_timeout' in setup:
        timeout = setup['network_timeout'].as_int()
        if timeout:
            set_timeout(timeout)

    # Prefix directory
    new_prefix = None
    create_dir = None
    if options.prefix is not None:
        new_prefix = options.prefix
        create_dir = options.prefix
    elif 'prefix_directory' in setup:
        create_dir = setup['prefix_directory'].as_text()
    else:
        new_prefix = os.getcwd()

    if create_dir:
        if not os.path.isdir(create_dir):
            os.makedirs(create_dir)
        else:
            raise InstallationError(
                u'Installation directory %s already exists',
                create_dir)
    if new_prefix:
        setup['prefix_directory'] = new_prefix

    setup['configuration_directory'] = configuration.get_cfg_directory()
    setup['bin_directory'].register(create_directory)
    setup['etc_directory'].register(create_directory)
    setup['lib_directory'].register(create_directory)
    setup['log_directory'].register(create_directory)
    setup['var_directory'].register(create_directory)
    setup['run_directory'].register(create_directory)

    # Lookup python executable
    if 'python_executable' not in setup:
        setup['python_executable'] = sys.executable

    utilities = configuration.utilities
    utilities.register('releases', Loaders)
    utilities.register('sources', Sources)
    utilities.register('kgs', KGS)
    utilities.register('package', current_package)
    utilities.register('installed', configuration.get_previous_cfg)
    utilities.events.subscribe('savepoint', configuration.save)
    utilities.events.subscribe('savepoint', logs.save)


class BootstrapCommand(object):
    """Basic command to bootstrap the project.
    """

    def options(self):
        parser = OptionParser()
        parser.add_option(
            "-c", "--configuration", dest="config", default='monteur.cfg',
            help="configuration file to use (default to monteur.cfg)")
        parser.add_option(
            "-p", "--prefix", dest="prefix",
            help="prefix directory for installation")
        parser.add_option(
            "-o", "--offline", dest="offline", action="store_true",
            help="run without network access")
        parser.add_option(
            "-t", "--timeout", dest="timeout", type="int",
            help="timeout on network access")
        parser.add_option(
            "-v", '--verbose', dest="verbosity", action="count", default=0,
            help="be verbose, use multiple times to increase verbosity level")
        parser.add_option(
            "-d", '--debug', dest="debug", action='store_true',
            help="debug installation system on unexpected errors")
        return parser

    def get_commands(self, session):
        """Pick a command to run it.
        """
        return [EggInfoCommand, Installer]

    def __call__(self):
        """Main entry point of the setup script.
        """
        parser = self.options()
        (options, args) = parser.parse_args()
        logs.configure(options.verbosity, options.debug)

        session = Session(options, args)
        session.events.subscribe('bootstrap', bootstrap)
        try:
            session(*self.get_commands(session))
        except Exception:
            logs.report(fatal=True, configuration=session.configuration)


class SetupCommand(BootstrapCommand):
    """Setup command.
    """

    def get_commands(self, session):
        """Pick a command and run it.
        """
        commands = working_set.list_entry_points('setup_commands')
        if len(session.args):
            name = session.args[0]
            command = commands.get(name, None)
            if command is None:
                raise InstallationError(u'Unknow command %s' % name)
        else:
            command = commands.get('default', None)
            if command is None:
                raise InstallationError(u'No command available')
        return [working_set.get_entry_point(
            'setup_commands', command['name'])]


def setup():
    command = SetupCommand()
    command()
