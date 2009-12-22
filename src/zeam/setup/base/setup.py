

from optparse import OptionParser
import sys
import os
import shutil

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.distribution import Environment, DevelopmentRelease
from zeam.setup.base.error import InstallationError

DEFAULT_CONFIG_DIR = '.zsetup'
DEFAULT_CONFIG_FILE = 'default.cfg'
DEFAULT_DIR_TO_CREATE = ['bin-directory',
                         'download-directory',
                         'lib-directory',
                         'log-directory',
                         'var-directory',]

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
            print 'Cannot setup default configuration'
            sys.exit(-1)
    return default_cfg


def setup_environment(config, options):
    setup = config['setup']

    # Network timeout
    if 'network-timeout' in setup:
        timeout = setup['network-timeout'].as_int()
        if timeout:
            socket.settimeout(timeout)

    # Prefix directory
    new_prefix = None
    create_dir = None
    if options.prefix is not None:
        new_prefix = options.prefix
        create_dir = options.prefix
    elif 'prefix-directory' in setup:
        create_dir = setup['prefix-directory'].as_text()
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
        setup['prefix-directory'] = new_prefix

    # Setup bin and co
    for directory in DEFAULT_DIR_TO_CREATE:
        path = setup[directory].as_text()
        if not os.path.isdir(path):
            os.makedirs(path)

    # Create an environment with develop packages
    environment = Environment()
    if 'develop' in setup:
        for path in setup['develop'].as_list():
            environment.add(DevelopmentRelease(path))
    return environment


def setup():
    parser = OptionParser()
    parser.add_option("-c", "--configuration", dest="config",
                      help="Configuration file to use (default to setup.cfg)",
                      default='setup.cfg')
    parser.add_option("-p", "--prefix", dest="prefix",
                      help="Prefix directory for installation")

    (options, args) = parser.parse_args()
    try:
        config = Configuration.read(options.config)
        config += Configuration.read(get_default_cfg())

        env = setup_environment(config, options)
        setup = config['setup']
        for section_name in setup['install'].as_list():
            section = config[section_name]
            print section['recipe'].as_text()

    except InstallationError, e:
        print e.msg()
        sys.exit(-1)

