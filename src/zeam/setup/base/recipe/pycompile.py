
import logging


from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.recipe import compile
from zeam.setup.base.python import PythonInterpreter
from zeam.setup.base.recipe.utils import MultiTask

logger = logging.getLogger('zeam.setup')


class PythonCompileFile(Recipe):

    def __init__(self, options, status):
        super(PythonCompileFile, self).__init__(options, status)
        self.interpreter = PythonInterpreter.detect(
            options.get_with_default(
                'python_executable', 'setup').as_text())
        self._do = MultiTask(options, 'compile')

    def install(self):

        def compile_files(path):
            logger.info('Compile python files in %s.' % path)
            self.interpreter.execute_module(compile, path)
            return path

        self._do(compile_files, self.status.paths.get_added(directory=True))
