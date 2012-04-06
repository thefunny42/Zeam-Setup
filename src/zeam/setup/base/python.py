
import sys
import tempfile
import atexit
import os
import logging
import shutil
import threading

from zeam.setup.base.archives import ZipArchive
from zeam.setup.base.utils import get_cmd_output
from zeam.setup.base.setuptools import setuptoolize, install_setuptools
from zeam.setup.base.error import InstallationError

logger = logging.getLogger('zeam.setup')


class PythonInterpreter(object):
    """Wrap and gives information about a python interpreter.
    """
    INTERPRETERS = {}

    def __init__(self, path):
        assert path is not None
        self._path = get_cmd_output(
            path, "-c",
            "print __import__('sys').executable")[0].strip()
        self._version = get_cmd_output(
            path, "-c",
            "print '.'.join(map(str, __import__('sys').version_info[:2]))"
            )[0].strip()
        self._platform = get_cmd_output(
            path, "-c",
            "print __import__('distutils.util').util.get_platform()")[0].strip()
        self._setuptools = {}
        self._lock = threading.RLock()

    @classmethod
    def detect(cls, path=None):
        if path is None:
            path = sys.executable
        if path in cls.INTERPRETERS:
            return cls.INTERPRETERS[path]
        interpreter = cls(path)
        cls.INTERPRETERS[path] = interpreter
        return interpreter

    def __eq__(self, string):
        return str(self) == string

    def __str__(self):
        return self._path

    def __repr__(self):
        return self._path

    def execute_external(self, *command, **opts):
        """Run an external command with the given args.
        """
        cmd = [self._path]
        cmd.extend(command)
        return get_cmd_output(*cmd, **opts)

    def execute_module(self, module, *args, **opts):
        """Run the given module with the given args.
        """
        module_file = module.__file__
        if module_file.endswith('.pyc'):
            module_file = module_file[:-1]
        cmd = [self._path]
        if 'python_options' in opts:
            cmd.extend(opts['python_options'])
            del opts['python_options']
        cmd.append(module_file)
        cmd.extend(args)
        return get_cmd_output(*cmd, **opts)

    def execute_setuptools(self, *cmd, **options):
        """Execute a setuptools command with this interpreter.
        """
        version = options.get('setuptools_version')
        if version not in self._setuptools:
            self._lock.acquire()
            try:
                if version not in self._setuptools:
                    self._setuptools[version] = find_setuptools(
                        self, setuptools_version=version)
            finally:
                self._lock.release()

        if self._setuptools[version] is not None:
            options.setdefault('environ', {})
            options['environ']['PYTHONPATH'] = self._setuptools[version]
            options['python_options'] = ['-S']
        return self.execute_module(setuptoolize, *cmd, **options)

    def get_pyversion(self):
        return self._version

    def get_platform(self):
        return self._platform


def find_setuptools(interpreter, setuptools_version=None):
    install_path = tempfile.mkdtemp('zeam.setup.setuptools')
    atexit.register(shutil.rmtree, install_path)
    stdout, stderr, code = interpreter.execute_module(
        install_setuptools, install_path, setuptools_version or 'default',
        python_options=['-S'])
    installed = os.listdir(install_path)
    if code or len(installed) != 1:
        stdout, stderr, code = interpreter.execute_external(
            '-c', 'import setuptools')
        if code:
            raise InstallationError(
                u"Setuptools installation failed."
                u"Please sent an insult to setuptools author.")
        logger.critical(
            u"ERROR: Setuptools installation failed. "
            u"We will try to continue with the version "
            u"installed on the system, but that might "
            u"trigger random unincomphrensible errors.")
        setuptools_path = None
    else:
        setuptools_path = os.path.join(install_path, installed[0])
        if os.path.isfile(setuptools_path):
            # We got a zip. Unzip it.
            temp_path = os.path.join(install_path, 'archive.zip')
            os.rename(setuptools_path, temp_path)
            os.mkdir(setuptools_path)
            archive = ZipArchive(temp_path, 'r')
            archive.extract(setuptools_path)
    return setuptools_path

