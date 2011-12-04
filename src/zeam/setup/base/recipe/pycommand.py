
import logging
import shlex

from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.error import InstallationError
from zeam.setup.base.python import PythonInterpreter


logger = logging.getLogger('zeam.setup')


class PythonCommand(Recipe):

    def __init__(self, configuration):
        super(PythonCommand, self).__init__(configuration)
        self.commands = configuration.get('python_commands', '').as_list()
        self.interpreter = PythonInterpreter.detect(
            self.configuration.get_with_default(
                'python_executable', 'setup').as_text())

    def install(self, status):
        for path in status.paths:
            logger.info('Run Python command in %s.' % path)
            for command in self.commands:
                options = dict(path=path)
                stdout, stdin, code = self.interpreter.execute_external(
                    *shlex.split(command), **options)
                if code:
                    raise InstallationError(
                        u"Python command failed", '\n' + (stdout or stdin))
