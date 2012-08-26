
from StringIO import StringIO
import logging
import os
import stat
import pprint

from monteur.distribution.release import Release
from monteur.error import InstallationError
from monteur.error import PackageError, PackageNotFound
from monteur.egginfo.loader import EggLoader
from monteur.python import PythonInterpreter
from monteur.version import Requirement, IncompatibleRequirement

logger = logging.getLogger('monteur')

SCRIPT_TEMPLATE = """#!%(executable)s %(flags)s

import sys
sys.path[0:0] = %(paths)s

%(script)s
"""

ISOLATED_SCRIPT_TEMPLATE = """#!%(executable)s -S %(flags)s

import sys
sys.path[0:0] = %(paths)s

import site
%(script)s
"""



def load_package(path, interpretor):
    release = Release()
    egg_info = os.path.join(path, 'EGG-INFO')
    if os.path.isdir(egg_info):
        return EggLoader(path, egg_info, release).load()
    return None


class ReleaseSet(object):
    """Represent the set of release used together.
    """

    def __init__(self):
        self.clear()

    def clear(self):
        self.releases = {}

    def __len__(self):
        return len(self.releases)

    def __iter__(self):
        return self.releases.itervalues()

    def __contains__(self, other):
        if isinstance(other, Requirement):
            release = self.releases.get(other.key)
            if release is not None:
                if not other.match(release):
                    raise IncompatibleRequirement(other, release)
                return True
            return False
        if isinstance(other, basestring):
            return other in self.releases
        raise ValueError(other)

    def __getitem__(self, requirement):
        release = self.get(requirement)
        if release is None:
            raise KeyError(requirement)
        return release

    def get(self, other, default=None):
        if isinstance(other, Requirement):
            return self.releases[other.key]
        if isinstance(other, basestring):
            return self.releases[other]
        raise default


    def add(self, release):
        """Try to add a new release in the environment. This doesn't
        add any dependencies by magic, you need to add them yourself
        by hand.
        """
        if not isinstance(release, Release):
            raise TypeError(u'Can only add release to a working set')
        if release.key not in self.releases:
            self.releases[release.key] = release
        else:
            installed = self.releases[release.key]
            if installed.path == release.path:
                self.releases[release.key] = release
            else:
                raise InstallationError(
                    u'Two release %s (installed in %s) and '
                    u'%s (installed in %s) added in the working set.' % (
                        repr(release), release.package_path,
                        repr(installed), release.package_path))

    def extend(self, working_set):
        """Extend the set with an another one.
        """
        if not isinstance(working_set, ReleaseSet):
            raise TypeError(u'Can only extend a set with an another one')
        for release in working_set.releases.values():
            self.add(release)

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
            raise InstallationError(u"Invalid entry point designation.", name)
        if package not in self.releases:
            raise PackageNotFound(package)
        release = self.releases[package]
        return release.get_entry_point(group, entry_name)

    def iter_all_entry_points(self, group, *package_keys):
        """Return all entry points for a given group in a list of packages.
        """
        if not package_keys:
            package_keys = self.releases.keys()
        for package_key in package_keys:
            if package_key not in self.releases:
                raise PackageError(
                    u"No package called %s in the environment." % package_key)
            package = self.releases[package_key]
            for entry_point in package.iter_all_entry_points(group):
                yield entry_point

    def list_entry_points(self, group, *package_keys):
        """List package package_key entry point in the given group.
        """
        if not package_keys:
            package_keys = self.releases.keys()
        entry_points = {}
        for package_key in package_keys:
            if package_key not in self.releases:
                raise PackageError(
                    u"No package called %s in the environment." % package_key)
            package = self.releases[package_key]
            package_entry_points = package.entry_points.get(group, None)
            if package_entry_points is not None:
                for name, destination in package_entry_points.items():
                    if name in entry_points:
                        raise PackageError(
                            u"Conflict between entry points called %s." % name)
                    entry_points[name] = {'destination': destination,
                                          'name': package_key + ':' + name}
        return entry_points

    def as_requirements(self):
        """Display as a list of a requirements (formatted as str).
        """
        return map(str, self.releases.values())


class WorkingSet(ReleaseSet):
    """Represent the set of release used together.
    """

    def __init__(self, interpretor=None, no_defaults=False, no_activate=True):
        self.interpretor = PythonInterpreter.detect(
            interpretor , not no_activate)
        self.clear(no_defaults)

    def clear(self, no_defaults=False):
        self.releases = {}
        self.releases['python'] = Release(
            name='python', version=self.interpretor.get_version())

        if not no_defaults:
            for path in self.interpretor.get_python_path():
                package = load_package(path, self.interpretor)
                if package is not None:
                    self.add(package)

    def create_script(self, script_path, script_body,
                      extra_paths=[], extra_flags='', script_isolation=False):
        """Create a script at the given path with the given body.
        """
        logger.info('Creating script %s.' % script_path)
        paths = StringIO()
        printer = pprint.PrettyPrinter(stream=paths, indent=2)
        printer.pprint(
            filter(lambda path: path is not None,
                   map(lambda r: r.path, self.releases.values())
                   + extra_paths))
        template = SCRIPT_TEMPLATE
        if script_isolation:
            template = ISOLATED_SCRIPT_TEMPLATE
        script_fd = open(script_path, 'w')
        script_fd.write(template % {
                'flags': extra_flags,
                'executable': self.interpretor,
                'paths': paths.getvalue(),
                'script': script_body})
        script_fd.close()
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
        return script_path



working_set = WorkingSet(no_activate=False)
