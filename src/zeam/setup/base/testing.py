
import os
import warnings
import unittest
import logging

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


def load_test_suite(test_module_names):
    """Load the test_suite from the test_files.
    """
    for test_module_name in test_module_names:
        try:
            test_module = __import__(
                test_module_name, globals(), globals(), 'test_suite')
        except ImportError:
            warnings.warn(
                "Cannot load Python module %s" % test_module_name,
                UserWarning)
            continue
        test_suite = getattr(test_module, 'test_suite', None)
        if test_suite is None:
            test_suite = unittest.defaultTestLoader.loadTestsFromModule(
                test_module)
        else:
            test_suite = test_suite()
        yield test_suite


def find_tests(package_name):
    """Load test suites from the given package name.
    """
    try:
        python_module = __import__(package_name, globals(), globals(), 'test')
    except ImportError:
        raise InstallationError('Cannot import tested module %s' % package_name)
    test_module_names = find_test_files(
        os.path.dirname(python_module.__file__),
        python_module.__name__)
    return load_test_suite(test_module_names)


class Test(object):
    """Command used to run tests.
    """

    def __init__(self, config, environment):
        self.config = config
        self.environment = environment
        self.package_name = config['egginfo']['name'].as_text()

    def run(self):
        __status__ = u"Running tests for %s" % self.package_name
        logger.warning(__status__)
        suite = unittest.TestSuite()
        suite.addTests(find_tests(self.package_name))
        verbosity = self.config['setup']['verbosity'].as_int()
        results = unittest.TextTestRunner(verbosity=verbosity).run(suite)

