
import atexit
import logging
import os
import shutil
import tempfile


from zeam.setup.base.egginfo.loader import EggLoader
from zeam.setup.base.setuptools import setuptoolize

logger = logging.getLogger('zeam.setup')

def find_egg_info(distribution, base_path):
    """Go through a path to find an egg-info directory.
    """
    wanted_directory = distribution.name + '.egg-info'
    for path, directories, filenames in os.walk(base_path):
        if wanted_directory in directories:
            return path, os.path.join(path, wanted_directory)
    return None, None

def create_manifest_from_source(source_file, manifest_file):
    """Create a missing manifest file from an existing source file.
    """
    source = open(source_file, 'r')
    manifest = open(manifest_file, 'w')
    for line in source.readlines():
        line = line.strip()
        if line:
            manifest.write('include ' + line + '\n')
    source.close()
    manifest.close()


class NativeSetuptoolsLoader(EggLoader):

    def install(self, install_path):
        # Remove egg_info to prevent strange things to happen
        shutil.rmtree(self.egg_info)

        result, error, code = self.execute(
            'bdist_egg', '-k', '--bdist-dir', install_path,
            path=self.distribution.package_path)
        if code:
            logger.debug(
                u"Setuptools retuned status code %s, "
                u"while installing in %s: %s %s" % (
                    code, install_path, result, error))


class NativeSetuptoolsLoaderFactory(object):
    """Load a setuptool source package.
    """

    def __init__(self):
        try:
            import setuptools
            self.setuptools_path = None
        except ImportError:
            logger.info('Installing setuptools')
            from ez_setup import download_setuptools
            self.setuptools_path = tempfile.mkdtemp('zeam.setup.setuptools')[1]
            download_setuptools(to_dir=self.setuptools_path)
            atexit.register(shutil.rmtree, self.setuptools_path)

    def setuptools(self, interpreter):

        def run(*cmd, **options):
            if self.setuptools_path is not None:
                options.setdefault('environ', {})
                options['environ']['PYTHONPATH'] = self.setuptools_path
            return interpreter.execute_module(setuptoolize, *cmd, **options)

        return run

    def __call__(self, distribution, path, interpretor):
        setup_py = os.path.join(path, 'setup.py')
        if os.path.isfile(setup_py):
            # You need to clean first the egg_info. install_requires
            # will trigger strange things only if it exists.
            egg_info_parent, egg_info = find_egg_info(distribution, path)
            if egg_info is not None and os.path.isdir(egg_info):
                # We will use the egg SOURCES.txt as input for a
                # MANIFEST if it doesn't exists. Most of packages miss
                # on and won't install everything without one.
                source_file = os.path.join(egg_info, 'SOURCES.txt')
                manifest_file = os.path.join(path, 'MANIFEST.in')
                if (os.path.isfile(source_file) and
                    not os.path.isfile(manifest_file)):
                    create_manifest_from_source(source_file, manifest_file)
                shutil.rmtree(egg_info)

            # Get fresh egg_info
            execute = self.setuptools(interpretor)
            output, _, code = execute('egg_info', path=path)
            if not code:
                egg_info_parent, egg_info = find_egg_info(distribution, path)
                if egg_info is not None and os.path.isdir(egg_info):
                    return NativeSetuptoolsLoader(
                        path, egg_info, distribution,
                        source_path=egg_info_parent, execute=execute)
                else:
                    logger.debug(
                        u"Could not read setup tools output %s in  %s, " % (
                            output, path))
            else:
                logger.debug(
                    u"Setuptools retuned status code %s in  %s, " % (
                        code, path))
        return None
