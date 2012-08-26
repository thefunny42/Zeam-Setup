
import logging


from monteur.recipe.recipe import Recipe
from monteur.recipe import compile
from monteur.python import PythonInterpreter
from monteur.recipe.utils import MultiTask

logger = logging.getLogger('monteur')


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

        self._do(
            compile_files,
            self.status.paths.query(
                added=True, directory=True))
