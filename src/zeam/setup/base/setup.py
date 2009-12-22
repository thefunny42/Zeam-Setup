
from optparse import OptionParser
import logging
import os
import shutil
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


def setup():
    parser = OptionParser()
    parser.add_option("-c", "--configuration", dest="config",
                      help="Configuration file to use (default to setup.cfg)",
                      default='setup.cfg')
    parser.add_option("-p", "--prefix", dest="prefix",
                      help="Prefix directory for installation")

    # Improve this logger configuration
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.INFO)

    (options, args) = parser.parse_args()
    try:
        logger.info('Reading configuration %s' % options.config)
        config = Configuration.read(options.config)
        logger.info('Reading default configuration')
        config += Configuration.read(get_default_cfg())

        installer = Installer(config, options)
        installer.run()
    except InstallationError, e:
        sys.stderr.write(e.msg())
        sys.exit(-1)

