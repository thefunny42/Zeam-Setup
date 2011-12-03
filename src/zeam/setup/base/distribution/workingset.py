
from StringIO import StringIO
import logging
import os
import stat
import sys
import pprint

from zeam.setup.base.distribution.release import Release, load_package
from zeam.setup.base.error import InstallationError
from zeam.setup.base.error import PackageError, PackageNotFound
from zeam.setup.base.python import PythonInterpreter
from zeam.setup.base.version import Requirement, IncompatibleRequirement

logger = logging.getLogger('zeam.setup')

SCRIPT_TEMPLATE = """#!%(executable)s

import sys
sys.path[0:0] = %(modules_path)s

%(script)s
"""

class WorkingSet(object):
    """Represent the set of release used together.
    """

    def __init__(self, interpretor=None):
        self.interpretor = PythonInterpreter.detect(interpretor)
        self.installed = {
            'python': Release(
                name='python', version=self.interpretor.get_pyversion())}

        if self.interpretor == sys.executable:
            for path in sys.path:
                package = load_package(path, self.interpretor)
                if package is not None:
                    self.add(package)

    def __len__(self):
        return len(self.installed)

    def __contains__(self, other):
        if isinstance(other, Requirement):
            release = self.installed.get(other.name)
            if release is not None:
                if not other.match(release):
                    raise IncompatibleRequirement(other, release)
                return True
            return False
        if isinstance(other, basestring):
            return other in self.installed
        raise ValueError(other)

    def get(self, other, default=None):
        if isinstance(other, Requirement):
            return self.installed[other.name]
        if isinstance(other, basestring):
            return self.installed[other]
        raise default

    def __getitem__(self, requirement):
        release = self.get(requirement)
        if release is None:
            raise KeyError(requirement)
        return release

    def add(self, release):
        """Try to add a new release in the environment. This doesn't
        add any dependencies by magic, you need to add them yourself
        by hand.
        """
        if not isinstance(release, Release):
            raise ValueError(u'Can only add release to a working set')
        if release.name not in self.installed:
            self.installed[release.name] = release
        else:
            installed = self.installed[release.name]
            if installed.path == release.path:
                self.installed[release.name] = release
            else:
                raise InstallationError(
                    u'Two release %s (installed in %s) and '
                    u'%s (installed in %s) added in the working set.' % (
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
            raise InstallationError(u"Invalid entry point designation", name)
        if package not in self.installed:
            raise PackageNotFound(package)
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

    def create_script(self, script_path, script_body, extra_paths=[]):
        """Create a script at the given path with the given body.
        """
        logger.warning('Creating script %s' % script_path)
        modules_path = StringIO()
        printer = pprint.PrettyPrinter(stream=modules_path, indent=2)
        printer.pprint(
            filter(lambda path: path is not None,
                   map(lambda r: r.path, self.installed.values())
                   + extra_paths))
        script_fd = open(script_path, 'w')
        script_fd.write(SCRIPT_TEMPLATE % {
                'executable': self.interpretor,
                'modules_path': modules_path.getvalue(),
                'script': script_body})
        script_fd.close()
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
        return script_path

    def as_requirements(self):
        """Display as a list of a requirements (formatted as str).
        """
        return map(str, self.installed.values())
