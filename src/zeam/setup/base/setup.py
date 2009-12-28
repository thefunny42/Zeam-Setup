
from optparse import OptionParser
import logging
import os
import shutil
import socket
import sys

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.distribution import Environment, DevelopmentRelease
from zeam.setup.base.error import InstallationError

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


def get_previous_cfg_path(config):
    """Return a path to the previous configuration used to setup this
    environment.
    """
    destination = config['setup']['prefix_directory'].as_text()
    zsetup_dest = os.path.join(destination, DEFAULT_CONFIG_DIR)
    if not os.path.isdir(zsetup_dest):
        os.makedirs(zsetup_dest)
    return os.path.join(zsetup_dest, 'installed.cfg')


def create_directory(directory):
    """Create a directory called directory if it doesn't exits
    already.
    """
    directory = directory.strip()
    if not os.path.isdir(directory):
        logger.info('Creating directory %s' % directory)
        os.makedirs(directory)


def bootstrap_cfg(config, options):
    """Bootstrap the configuration settings. Mainly set things like
    network_timeout, prefix_directory, python_executable.
    """
    setup = config['setup']

    # Network timeout
    if 'network_timeout' in setup:
        timeout = setup['network_timeout'].as_int()
        if timeout:
            socket.settimeout(timeout)

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

    # Lookup python executable
    if 'python_executable' not in setup:
        setup['python_executable'] = sys.executable

    # Create an environment with develop packages
    environment = Environment(setup['python_executable'])
    if 'develop' in setup:
        for path in setup['develop'].as_list():
            environment.add(DevelopmentRelease(path=path))
    return environment


def setup():
    """Main entry point of the setup script.
    """
    parser = OptionParser()
    parser.add_option("-c", "--configuration", dest="config",
                      help="Configuration file to use (default to setup.cfg)",
                      default='setup.cfg')
    parser.add_option("-p", "--prefix", dest="prefix",
                      help="Prefix directory for installation")

    # XXX Improve this logger configuration
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.INFO)

    (options, args) = parser.parse_args()
    try:
        logger.info(u'Reading configuration %s' % options.config)
        config = Configuration.read(options.config)
        logger.info(u'Reading default configuration')
        config += Configuration.read(get_default_cfg_path())

        environment = bootstrap_cfg(config, options)
        previous_config = None
        previous_cfg_path = get_previous_cfg_path(config)
        if os.path.isfile(previous_cfg_path):
            logger.info(u'Loading previous configuration')
            previous_config = Configuration.read(previous_cfg_path)

        all_commands = environment.list_entry_points('setup_commands')
        command = all_commands['default']
        if len(args):
            try:
                command = all_commands[args[0]]
            except KeyError:
                raise InstallationError(u'Unknow command %s' % args[0])

        command_class = environment.get_entry_point(
            'setup_commands', command['name'])
        processor = command_class(config, environment)
        processor.run()

        zsetup_fd = open(previous_cfg_path, 'w')
        config.write(zsetup_fd)
        zsetup_fd.close()

    except InstallationError, e:
        sys.stderr.write(e.msg())
        sys.exit(-1)

