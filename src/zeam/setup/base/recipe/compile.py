
import logging
import os
import py_compile

from zeam.setup.base.recipe.recipe import Recipe
from zeam.setup.base.distribution.loader import compile_py_files

logger = logging.getLogger('zeam.setup')

# XXX We should use the correct interpreter here

class PythonCompileFile(Recipe):

    def install(self, status):
        for path in status.paths:
            logger.info('Compile python files in %s.' % path)
            if os.path.isdir(path):
                compile_py_files(path)
            elif path.endswith('.py'):
                py_compile.compile(path)
