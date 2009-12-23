
from optparse import OptionParser
import logging
import os
import shutil
import socket
import sys

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.installer import Installer
from zeam.setup.base.error import InstallationError

DEFAULT_CONFIG_DIR = '.zsetup'
DEFAULT_CONFIG_FILE = 'default.cfg'

logger = logging.getLogger('zeam.setup')

def get_default_cfg():
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
    destination = config['setup']['prefix_directory'].as_text()
    zsetup_dest = os.path.join(destination, DEFAULT_CONFIG_DIR)
    if not os.path.isdir(zsetup_dest):
        os.makedirs(zsetup_dest)
    return os.path.join(zsetup_dest, 'installed.cfg')


def bootstrap_cfg(config, options):
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


def setup():
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
        config += Configuration.read(get_default_cfg())

        bootstrap_cfg(config, options)
        previous_config = None
        previous_cfg_path = get_previous_cfg_path(config)
        if os.path.isfile(previous_cfg_path):
            logger.info(u'Loading previous configuration')
            previous_config = Configuration.read(previous_cfg_path)

        installer = Installer(config, options)
        installer.run()

        zsetup_fd = open(previous_cfg_path, 'w')
        config.write(zsetup_fd)
        zsetup_fd.close()

    except InstallationError, e:
        sys.stderr.write(e.msg())
        sys.exit(-1)

