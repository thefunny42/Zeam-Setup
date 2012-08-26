
import logging
import os
import sys
import shutil

from monteur.configuration import Configuration
from monteur.distribution.workingset import working_set
from monteur.utils import create_directory

logger = logging.getLogger('monteur')

DEFAULT_CONFIG_DIR = '.monteur'
DEFAULT_CONFIG_FILE = 'default.cfg'
PREVIOUS_CONFIG_FILE = 'installed.cfg'


class Events(object):
    """A simple event system.
    """

    def __init__(self, *args):
        self._permanent = {}
        self._one_time = {}
        self._bounded = []
        self._default_args = args

    def bind(self, events):
        if events not in self._bounded:
            self._bounded.append(events)

    def unbind(self, events):
        if events in self._bounded:
            self._bounded.remove(events)

    def subscribe(self, event, callback):
        subscribers = self._permanent.setdefault(event, [])
        subscribers.append(callback)

    def one(self, event, callback):
        subscribers = self._one_time.setdefault(event, [])
        subscribers.append(callback)

    def __call__(self, event, *args):
        for bounded in self._bounded:
            bounded(event, *args)
        call_args = self._default_args + args
        if event in self._one_time:
            for callback in self._one_time[event]:
                callback(*call_args)
            del self._one_time[event]
        for callback in self._permanent.get(event, []):
            callback(*call_args)


class SessionConfiguration(Configuration):

    def get_previous_cfg_directory(self, *ignore):
        """Return the previous configuration directory.
        """
        destination = self['setup']['prefix_directory'].as_text()
        return create_directory(os.path.join(destination, DEFAULT_CONFIG_DIR))

    def get_previous_cfg(self, *ignore):
        """Return a previous configuration used to setup this environment.
        """
        directory = self.get_previous_cfg_directory()
        if directory is not None:
            filename = os.path.join(directory, PREVIOUS_CONFIG_FILE)
            if os.path.isfile(filename):
                logger.info(u'Loading previous configuration')
                return Configuration.read(filename)
        return Configuration()

    def save(self, *ignore):
        """Save current configuration into the previous one.
        """
        directory = self.get_previous_cfg_directory()
        filename = os.path.join(directory, PREVIOUS_CONFIG_FILE)
        logger.info(u'Saving installed configuration in %s', filename)
        stream = open(filename, 'w')
        try:
            self.write(stream)
        except:
            stream.close()


class Command(object):
    """Base class for commands.
    """

    def __init__(self, session):
        self.session = session

    def run(self):
        raise NotImplementedError


class MultiCommand(Command):
    """Base class for commands that support subcommands.
    """

    def do_help(self, args):
        """Display help about existing sub-commands.
        """

        def do_documentation(name):
            if name is not None:
                documentation = self.COMMANDS[name].__doc__
                if documentation:
                    documentation = documentation.strip()
                else:
                    documentation = u"No documentation available."
                logger.error(u"%s: %s", name, documentation)

        if args and args[0] in self.COMMANDS:
            do_documentation(args[0])
        else:
            logger.error("Available sub-commands:")
            for name in self.COMMANDS:
                do_documentation(name)
        return False

    COMMANDS = {
        "help": do_help,
        None: do_help}

    def initialize(self):
        pass

    def run(self):
        args = self.session.args
        if len(args) < 2:
            command = self.COMMANDS[None]
            args = []
        else:
            command = self.COMMANDS[args[1]]
            args = args[2:]
        self.initialize()
        return command(self, args)


class Session(object):

    def __init__(self, options, args):
        self.options = options
        self.args = args
        self.events = Events(self)
        self.configuration = None

    def get_default_cfg_directory(self):
        """Return the default configuration directory.
        """
        user_directory = os.path.expanduser('~')
        return create_directory(
            os.path.join(user_directory, DEFAULT_CONFIG_DIR))

    def get_default_cfg(self):
        """Return the default configuration.
        """
        directory = self.get_default_cfg_directory()
        filename = os.path.join(directory, DEFAULT_CONFIG_FILE)
        if not os.path.isfile(filename):
            try:
                shutil.copy(
                    os.path.join(os.path.dirname(__file__), 'default.cfg'),
                    filename)
            except IOError:
                sys.stderr.write('Cannot install default configuration.')
                sys.exit(-1)
        logger.info(u'Reading default configuration.')
        return Configuration.read(filename)

    def configure(self):
        assert self.configuration is None, u'Configuration already active.'
        logger.info(u'Reading configuration %s.', self.options.config)
        self.configuration = SessionConfiguration.read(self.options.config)
        self.configuration += self.get_default_cfg()
        self.configuration.utilities.register('events', Events)
        self.events.bind(self.configuration.utilities.events)
        self.events('bootstrap')

    def reconfigure(self):
        self.events.unbind(self.configuration.utilities.events)
        self.configuration.utilities.events('finish')
        self.configuration = None
        working_set.clear()
        self.configure()

    def need_reconfigure(self):
        self.events.one('transaction', lambda *args: self.reconfigure())

    def __call__(self, *commands):
        self.configure()
        queue = list(reversed(commands))
        command = queue.pop()
        while command is not None:
            self.events('transaction')
            if command(self).run():
                self.events('savepoint')
            command = None
            if queue:
                command = queue.pop()
        self.events('finish')
