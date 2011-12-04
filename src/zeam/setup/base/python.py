
import sys

from zeam.setup.base.utils import get_cmd_output


class PythonInterpreter(object):
    """Wrap and gives information about a python interpreter.
    """
    INTERPRETERS = {}

    def __init__(self, path):
        assert path is not None
        self.__path = get_cmd_output(
            path, "-c",
            "print __import__('sys').executable")[0].strip()
        self.__version = get_cmd_output(
            path, "-c",
            "print '.'.join(map(str, __import__('sys').version_info[:2]))"
            )[0].strip()
        self.__platform = get_cmd_output(
            path, "-c",
            "print __import__('sys').platform")[0].strip()

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
        return self.__path

    def __repr__(self):
        return self.__path

    def execute_external(self, *command, **opts):
        """Run an external command with the given args.
        """
        cmd = [self.__path]
        cmd.extend(command)
        return get_cmd_output(*cmd, **opts)

    def execute_module(self, module, *args, **opts):
        """Run the given module with the given args.
        """
        module_file = module.__file__
        if module_file.endswith('.pyc'):
            module_file = module_file[:-1]
        cmd = [self.__path, module_file]
        cmd.extend(args)
        return get_cmd_output(*cmd, **opts)

    def get_pyversion(self):
        return self.__version

    def get_platform(self):
        return self.__platform
