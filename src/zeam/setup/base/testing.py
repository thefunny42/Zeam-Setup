
import os
import unittest
import logging

from zeam.setup.base.error import PackageError
from zeam.setup.base.session import Command

logger = logging.getLogger('zeam.setup')


def path_to_module_name(
    base_directory, base_name, module_directory, module_name):
    """Compute the name of a Python module from its place on the
    filesystem (given a parent Python module and its folder)
    """
    module = module_directory[len(base_directory) + 1:]
    module = module.replace(os.path.sep, '.')
    module_name, _ = os.path.splitext(module_name)
    return '.'.join((base_name, module, module_name))

def find_test_files(module_directory, module_name):
    """Locate files which migth contain tests in the module directory.
    """
    for path, directories, filenames in os.walk(module_directory):
        if 'tests.py' in filenames:
            yield path_to_module_name(
                module_directory, module_name, path, 'tests.py')
        if path.endswith('tests'):
            filenames.sort()
            for filename in filenames:
                if filename.startswith('test_') and filename.endswith('.py'):
                    yield path_to_module_name(
                        module_directory, module_name, path, filename)


def load_test_suite(module_names):
    """Load the test_suite from the test_files.
    """
    for module_name in module_names:
        try:
            module = __import__(
                module_name, globals(), globals(), 'test_suite')
        except ImportError, error:
            raise PackageError(
                u"Cannot import Python module", module_name, detail=str(error))
        suite = getattr(module, 'test_suite', None)
        if suite is None:
            suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        else:
            suite = suite()
        yield suite

def find_tests(package_name):
    """Load test suites from the given package name.
    """
    try:
        python_module = __import__(package_name, globals(), globals(), 'test')
    except ImportError, error:
        raise PackageError(
            u'Cannot import Package module', package_name, detail=str(error))
    module_names = find_test_files(
        os.path.dirname(python_module.__file__),
        python_module.__name__)
    return load_test_suite(module_names)


class TestCommand(Command):
    """Command used to run tests.
    """

    def __init__(self, session):
        self.configuration = session.configuration
        self.package_name = self.configuration['egginfo']['name'].as_text()

    def run(self):
        __status__ = u"Running tests for %s" % self.package_name
        logger.warning(__status__)
        suite = unittest.TestSuite()
        suite.addTests(find_tests(self.package_name))
        verbosity = self.configuration['setup']['verbosity'].as_int()
        # Disable logger except for error while running the tests.
        log_level = logger.level
        logger.setLevel(logging.FATAL)
        unittest.TextTestRunner(verbosity=verbosity).run(suite)
        logger.setLevel(log_level)
        return False
