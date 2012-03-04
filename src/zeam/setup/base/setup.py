
from optparse import OptionParser
import logging
import os
import shutil
import socket
import sys

from zeam.setup.base.distribution.kgs import KGS
from zeam.setup.base.distribution.workingset import working_set
from zeam.setup.base.distribution.release import current_package, Loaders
from zeam.setup.base.configuration import Configuration
from zeam.setup.base.error import InstallationError, logs
from zeam.setup.base.recipe.commands import Installer
from zeam.setup.base.utils import create_directory
from zeam.setup.base.sources.sources import Sources
from zeam.setup.base.egginfo.commands import EggInfo

DEFAULT_CONFIG_DIR = '.zsetup'
DEFAULT_CONFIG_FILE = 'default.cfg'

logger = logging.getLogger('zeam.setup')


def get_default_cfg_path():
    """Return a path to the default configuration stored in user
    directory.
    """
    user_dir = os.path.expanduser('~')
    setup_dir = os.path.join(user_dir, DEFAULT_CONFIG_DIR)
    if not os.path.isdir(setup_dir):
        os.mkdir(setup_dir)
    default_cfg = os.path.join(setup_dir, DEFAULT_CONFIG_FILE)
    if not os.path.isfile(default_cfg):
        try:
            shutil.copy(
                os.path.join(os.path.dirname(__file__), 'default.cfg'),
                default_cfg)
        except IOError:
            sys.stderr.write('Cannot setup default configuration')
            sys.exit(-1)
    return default_cfg


def get_previous_cfg_path(configuration):
    """Return a path to the previous configuration used to setup this
    environment.
    """
    destination = configuration['setup']['prefix_directory'].as_text()
    zsetup_path = os.path.join(destination, DEFAULT_CONFIG_DIR)
    if not os.path.isdir(zsetup_path):
        os.makedirs(zsetup_path)
    return os.path.join(zsetup_path, 'installed.cfg')


def get_previous_cfg(configuration):
    """Return a previous configuration used to setup this environment.
    """
    cfg_path = get_previous_cfg_path(configuration)
    if os.path.isfile(cfg_path):
        logger.info(u'Loading previous configuration')
        return Configuration.read(cfg_path)
    return Configuration()


def bootstrap_cfg(config, options):
    """Bootstrap the configuration settings. Mainly set things like
    network_timeout, prefix_directory, python_executable.
    """
    __status__ = u"Initializing environment."
    setup = config['setup']

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

    setup['bin_directory'].register(create_directory)
    setup['lib_directory'].register(create_directory)
    setup['log_directory'].register(create_directory)
    setup['var_directory'].register(create_directory)
    setup['run_directory'].register(create_directory)

    # Lookup python executable
    if 'python_executable' not in setup:
        setup['python_executable'] = sys.executable

    config.utilities.register('releases', Loaders)
    config.utilities.register('sources', Sources)
    config.utilities.register('kgs', KGS)
    config.utilities.register('package', current_package)
    config.utilities.register('installed', get_previous_cfg)

    def save_configuration():
        save_path = get_previous_cfg_path(config)
        logger.info(u'Saving installed configuration in %s', save_path)
        save_file = open(save_path, 'w')
        config.write(save_file)
        save_file.close()

    config.utilities.atexit.register(save_configuration)


class BootstrapCommand(object):
    """Basic command to bootstrap the project.
    """

    def options(self):
        parser = OptionParser()
        parser.add_option(
            "-c", "--configuration", dest="config", default='setup.cfg',
            help="configuration file to use (default to setup.cfg)")
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

    def command(self, configuration, options, args):
        """Pick a command and run it.
        """
        EggInfo(configuration).run()
        Installer(configuration).run()

    def run(self):
        """Main entry point of the setup script.
        """
        parser = self.options()
        (options, args) = parser.parse_args()
        logs.configure(options.verbosity, options.debug)

        configuration = None
        try:
            logger.info(u'Reading configuration %s' % options.config)
            configuration = Configuration.read(options.config)
            logger.info(u'Reading default configuration')
            configuration += Configuration.read(get_default_cfg_path())

            bootstrap_cfg(configuration, options)

            self.command(configuration, options, args)

            configuration.utilities.atexit.execute()
        except Exception:
            logs.report(fatal=True, configuration=configuration)


class SetupCommand(BootstrapCommand):
    """Setup command.
    """

    def command(self, configuration, options, args):
        """Pick a command and run it.
        """
        commands = working_set.list_entry_points('setup_commands')
        if len(args):
            command = commands.get(args[0], None)
            if command is None:
                raise InstallationError(u'Unknow command %s' % args[0])
        else:
            command = commands.get('default', None)
            if command is None:
                raise InstallationError(u'No command available')
        command_class = working_set.get_entry_point(
            'setup_commands', command['name'])
        processor = command_class(configuration)
        processor.run()


def setup():
    SetupCommand().run()
