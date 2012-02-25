
import logging
import os
import shutil
import py_compile

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.egginfo.write import write_egg_info
from zeam.setup.base.error import PackageError
from zeam.setup.base.python import PythonInterpreter
from zeam.setup.base.setuptools.autotools import AutomakeBuilder
from zeam.setup.base.version import Version, Requirements

logger = logging.getLogger('zeam.setup')

builder = AutomakeBuilder()


def find_packages(source_dir):
    """Return a list of package contained in the given directory.
    """
    for possible_package in os.listdir(source_dir):
        possible_path = os.path.join(source_dir, possible_package)
        if (os.path.isfile(os.path.join(possible_path, '__init__.py')) or
            os.path.isfile(os.path.join(possible_path, '__init__.pyc'))):
            yield possible_package


def compile_py_files(source_dir):
    """Compile if possible all Python files.
    """
    # XXX Should use os.walk ?
    # XXX We should use the correct interpreter here
    for source_file in os.listdir(source_dir):
        source_path = os.path.join(source_dir, source_file)
        if source_path.endswith('.py') and os.path.isfile(source_path):
            try:
                py_compile.compile(source_path, doraise=True)
            except:
                pass
        elif os.path.isdir(source_path):
            compile_py_files(source_path)


def install_py_packages(target_dir, source_dir, packages):
    """Install Python packages from source_dir into target_dir.
    """
    for package in packages:
        target_package_dir = os.path.join(target_dir, package)
        logger.info("Install Python files for %s into %s" % (
                package, target_package_dir))
        if os.path.isdir(target_package_dir):
            logger.debug("Cleaning installation directory %s" % (
                    target_package_dir))
            shutil.rmtree(target_package_dir)
        # XXX We should here copy only manifest files.
        shutil.copytree(
            os.path.join(source_dir, package), target_package_dir)
        compile_py_files(target_package_dir)



class SetupLoader(object):

    def __init__(self, configuration, distribution, interpretor=None):
        self.path = configuration.get_cfg_directory()
        self.configuration = configuration
        self.distribution = distribution
        if interpretor is None:
            interpretor = PythonInterpreter.detect(
                configuration['setup']['python_executable'].as_text())
        self.interpretor = interpretor

    def load(self):
        egginfo = self.configuration['egginfo']
        self.distribution.name = egginfo['name'].as_text()
        self.distribution.version = Version.parse(egginfo['version'].as_text())
        self.distribution.summary = egginfo.get('summary', '').as_text()
        self.distribution.author = egginfo.get('author', '').as_text()
        self.distribution.author_email = egginfo.get(
            'author_email', '').as_text()
        self.distribution.license = egginfo.get('license', '').as_text()
        self.distribution.classifiers = egginfo.get('classifier', '').as_list()
        self.distribution.format = None
        self.distribution.pyversion = None
        self.distribution.platform = None
        self.distribution.requirements = Requirements.parse(
            egginfo.get('requires', '').as_list())
        self.distribution.extras = {}

        # Source path of the extension
        path = os.path.join(self.path, egginfo.get('source', '.').as_text())
        if not os.path.isdir(path):
            raise PackageError(path, 'Invalid source path "%s"' % path)
        self.distribution.path = os.path.abspath(path)
        self.distribution.package_path = self.path

        # Entry points
        self.distribution.entry_points = {}
        entry_points = egginfo.get('entry_points', None)
        if entry_points is not None:
            for category_name in entry_points.as_list():
                info = self.configuration['entry_points:' + category_name]
                self.distribution.entry_points[category_name] = info.as_dict()

        # XXX Experimental, should not be here, should be job of installer
        write_egg_info(self.distribution)
        return self.distribution

    def install(self, install_path):
        if self.distribution.extensions:
            builder.build(self.distribution, install_path, self.interpretor)

        try:
            install_py_packages(
                install_path,
                self.distribution.path,
                find_packages(self.distribution.path))

            # XXX This needs review
            if self.distribution.extensions:
                builder.install(
                    self.distribution, install_path, self.interpretor)

            write_egg_info(self.distribution, package_path=install_path)
        except:
            shutil.rmtree(install_path)
            raise


class SetupLoaderFactory(object):
    """Load a zeam.setup package.
    """

    def __init__(self, options):
        self.options = options

    def __call__(self, distribution, path, interpretor, trust=-99):
        setup_cfg = os.path.join(path, 'setup.cfg')
        if os.path.isfile(setup_cfg):
            configuration = Configuration.read(setup_cfg)
            if 'egginfo' in configuration.sections:
                return SetupLoader(configuration, distribution, interpretor)
            logger.debug("Missing zeam package configuration in %s" % setup_cfg)
        return None

