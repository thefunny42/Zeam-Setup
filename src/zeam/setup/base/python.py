
import sys
import tempfile
import atexit
import os
import logging
import shutil
import threading
import distutils

from zeam.setup.base.archives import ZipArchive
from zeam.setup.base.utils import get_cmd_output, have_cmd
from zeam.setup.base.setuptools import setuptoolize, install_setuptools
from zeam.setup.base.error import InstallationError

logger = logging.getLogger('zeam.setup')


class PythonInterpreter(object):
    """Wrap and gives information about a python interpreter.
    """
    INTERPRETERS = {}

    def __init__(self, path, readonly=False):
        assert path is not None
        if readonly and path == sys.executable:
            self._path = sys.executable
            self._platform = distutils.util.get_platform()
            self._python_path = sys.path
            self._version = ".".join(map(str, sys.version_info[:2]))
        else:
            have_python, version = have_cmd(
                path, '-c',
                'print "version", '
                '".".join(map(str, __import__("sys").version_info[:2]))')
            if not have_python:
                raise InstallationError(
                    "This configuration requires a specific Python "
                    "you don't have:",
                    path)
            self._version = version
            self._path = get_cmd_output(
                path, "-c",
                "print __import__('sys').executable")[0].strip()
            self._platform = None
            self._python_path = None
        self._setuptools = {}
        self._lock = threading.RLock()

    @classmethod
    def detect(cls, path=None, readonly=False):
        if path is None:
            path = sys.executable
        if (path, readonly) in cls.INTERPRETERS:
            return cls.INTERPRETERS[(path, readonly)]
        interpreter = cls(path, readonly=readonly)
        cls.INTERPRETERS[(path, readonly)] = interpreter
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
        version = options.get('version')
        if version not in self._setuptools:
            self._lock.acquire()
            try:
                if version not in self._setuptools:
                    self._setuptools[version] = find_setuptools(
                        self, version=version)
            finally:
                self._lock.release()

        if self._setuptools[version] is not None:
            options.setdefault('environ', {})
            options['environ']['PYTHONPATH'] = self._setuptools[version]
            options['python_options'] = ['-S']
        return self.execute_module(setuptoolize, *cmd, **options)

    def get_version(self):
        return self._version

    def get_platform(self):
        if self._platform is not None:
            return self._platform
        self._lock.acquire()
        try:
            if self._platform is None:
                result = self.execute_external(
                    "-c",
                    "print __import__('distutils.util')"
                    ".util.get_platform()")
                self._platform = result[0].strip()
        finally:
            self._lock.release()
        return self._platform

    def get_python_path(self):
        if self._python_path is not None:
            return self._python_path
        self._lock.acquire()
        try:
            if self._python_path is None:
                result = self.execute_external(
                    "-c",
                    "print '\\n'.join(__import__('sys').path)")
                self._python_path = result[0].strip().split('\n')
        finally:
            self._lock.release()
        return self._python_path


def find_setuptools(interpreter, version=None):
    install_path = tempfile.mkdtemp('zeam.setup.setuptools')
    atexit.register(shutil.rmtree, install_path)
    stdout, stderr, code = interpreter.execute_module(
        install_setuptools, install_path, version or 'default',
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
        return None
    setuptools_path = os.path.join(install_path, installed[0])
    if os.path.isfile(setuptools_path):
        # We got a zip. Unzip it.
        temp_path = os.path.join(install_path, 'archive.zip')
        os.rename(setuptools_path, temp_path)
        os.mkdir(setuptools_path)
        archive = ZipArchive(temp_path, 'r')
        archive.extract(setuptools_path)
    return setuptools_path

