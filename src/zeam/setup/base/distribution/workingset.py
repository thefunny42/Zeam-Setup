
from StringIO import StringIO
import logging
import os
import stat
import sys
import pprint

from zeam.setup.base.distribution.release import Release, load_package
from zeam.setup.base.version import Requirement, IncompatibleRequirement
from zeam.setup.base.error import PackageError, InstallationError
from zeam.setup.base.utils import get_cmd_output

logger = logging.getLogger('zeam.setup')

SCRIPT_TEMPLATE = """#!%(executable)s

import sys
sys.path[0:0] = %(modules_path)s

%(script)s
"""


class PythonInterpreter(object):
    """Wrap and gives information about a python interpreter.
    """

    INTERPRETERS = {}

    def __init__(self, path):
        assert path is not None
        self.__path = path
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

    def execute(self, module, *args):
        """Run the given module with the given args.
        """
        module_file = module.__file__
        if module_file.endswith('.pyc'):
            module_file = module_file[:-1]
        cmd = [self.__path, module_file]
        cmd.extend(args)
        return get_cmd_output(*cmd)[0]

    def get_pyversion(self):
        return self.__version

    def get_platform(self):
        return self.__platform


class WorkingSet(object):
    """Represent the set of release used together.
    """

    def __init__(self, interpretor=None):
        self.installed = {}
        self.__installer = None
        self.interpretor = PythonInterpreter.detect(interpretor)

        if self.interpretor == sys.executable:
            for path in sys.path:
                package = load_package(path, self.interpretor)
                if package is not None:
                    self.add(package)

    def __contains__(self, other):
        if isinstance(other, Requirement):
            release = self.installed.get(other.name)
            if release is not None:
                if not other.match(release):
                    raise IncompatibleRequirement(other, release)
                return True
            return False
        if isinstance(other, basestring):
            return other in self.__installed
        raise ValueError(other)

    def add(self, release):
        """Try to add a new release in the environment. This doesn't
        add any dependencies by magic, you need to add them yourself
        by hand.
        """
        if not isinstance(release, Release):
            raise ValueError(u'Can only add release to an environment')
        if release.name not in self.installed:
            self.installed[release.name] = release
        else:
            installed = self.installed[release.name]
            if installed.path == release.path:
                self.installed[release.name] = release
            else:
                raise InstallationError(
                    u'Two release %s (installed in %s) and '
                    u'%s (installed in %s) added in the environment.' % (
                        repr(release), release.package_path,
                        repr(installed), release.package_path))

    def get_entry_point(self, group, name):
        """Return the entry point value called name for the given group.
        """
        name_parts = name.split(':')
        package = name_parts[0]
        if len(name_parts) == 1:
            entry_name = 'default'
        elif len(name_parts) == 2:
            entry_name = name_parts[1]
        else:
            InstallationError('Invalid entry point designation %s' % name)
        if package not in self.installed:
            raise PackageError(u"Package %s not available" % package)
        release = self.installed[package]
        return release.get_entry_point(group, entry_name)

    def list_entry_points(self, group, *package_names):
        """List package package_name entry point in the given group.
        """
        if not package_names:
            package_names = self.installed.keys()
        entry_points = {}
        for package_name in package_names:
            if package_name not in self.installed:
                raise PackageError(
                    u"No package called %s in the environment" % package_name)
            package = self.installed[package_name]
            package_entry_points = package.entry_points.get(group, None)
            if package_entry_points is not None:
                for name, destination in package_entry_points.items():
                    if name in entry_points:
                        raise PackageError(
                            u"Conflict between entry points called %s" % name)
                    entry_points[name] = {'destination': destination,
                                          'name': package_name + ':' + name}
        return entry_points

    def create_script(self, script_path, script_body):
        """Create a script at the given path with the given body.
        """
        logger.warning('Creating script %s' % script_path)
        modules_path = StringIO()
        printer = pprint.PrettyPrinter(stream=modules_path, indent=2)
        printer.pprint(map(lambda r: r.path, self.installed.values()))
        script_fd = open(script_path, 'w')
        script_fd.write(SCRIPT_TEMPLATE % {
                'executable': self.interpretor,
                'modules_path': modules_path.getvalue(),
                'script': script_body})
        script_fd.close()
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
        return script_path
