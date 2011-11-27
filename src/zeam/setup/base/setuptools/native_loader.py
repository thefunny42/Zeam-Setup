
import atexit
import logging
import os
import shutil
import tempfile


from zeam.setup.base.egginfo.loader import EggLoader
from zeam.setup.base.setuptools import setuptoolize

logger = logging.getLogger('zeam.setup')



class NativeSetuptoolsLoader(EggLoader):

    def install(self, install_path):
        # Remove egg_info to prevent strange things to happen
        shutil.rmtree(self.egg_info)

        result, error, code = self.execute(
            'bdist_egg', '-k', '--bdist-dir', install_path,
            path=self.distribution.path)
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
            egg_info = os.path.join(
                path, '.'.join((distribution.name, 'egg-info')))
            # You need to clean first the egg_info. install_requires
            # will trigger strange things only if it exists.
            if os.path.isdir(egg_info):
                shutil.rmtree(egg_info)

            # Get fresh egg_info
            execute = self.setuptools(interpretor)
            output, _, code = execute('egg_info', '-e', '.', path=path)
            if not code:
                if os.path.isdir(egg_info):
                    return NativeSetuptoolsLoader(
                        path, egg_info, distribution, execute)
                else:
                    logger.debug(
                        u"Could not read setup tools output %s in  %s, " % (
                            output, path))
            else:
                logger.debug(
                    u"Setuptools retuned status code %s in  %s, " % (
                        code, path))
        return None
