
import logging


from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.recipe import compile
from zeam.setup.base.python import PythonInterpreter

logger = logging.getLogger('zeam.setup')


class PythonCompileFile(Recipe):

    def __init__(self, options):
        super(PythonCompileFile, self).__init__(options)
        self.interpreter = PythonInterpreter.detect(
            options.get_with_default(
                'python_executable', 'setup').as_text())

    def install(self, status):
        for path in status.paths.current:
            logger.info('Compile python files in %s.' % path)
            self.interpreter.execute_module(compile, path)
