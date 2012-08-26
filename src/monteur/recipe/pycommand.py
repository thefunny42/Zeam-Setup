
import logging
import shlex

from monteur.recipe.recipe import Recipe
from monteur.error import InstallationError
from monteur.python import PythonInterpreter

logger = logging.getLogger('monteur')


class PythonCommand(Recipe):

    def __init__(self, options, status):
        super(PythonCommand, self).__init__(options, status)
        self.commands = options.get('python_commands', '').as_list()
        self.interpreter = PythonInterpreter.detect(
            options.get_with_default(
                'python_executable', 'setup').as_text())

    def install(self):
        for path in self.status.paths.query(added=True, directory=True):
            logger.info('Run Python command in %s.' % path)
            for command in self.commands:
                options = dict(path=path)
                stdout, stdin, code = self.interpreter.execute_external(
                    *shlex.split(command), **options)
                if code:
                    raise InstallationError(
                        u"Python command failed", '\n' + (stdout or stdin))
