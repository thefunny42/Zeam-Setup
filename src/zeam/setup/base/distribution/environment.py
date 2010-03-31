
from StringIO import StringIO
import logging
import os
import stat
import sys
import pprint

from zeam.setup.base.distribution.release import Release
from zeam.setup.base.distribution.egg import EggRelease
from zeam.setup.base.error import PackageError, InstallationError
from zeam.setup.base.version import Requirement, Requirements

logger = logging.getLogger('zeam.setup')

SCRIPT_TEMPLATE = """#!%(executable)s

import sys
sys.path[0:0] = %(modules_path)s

%(script)s
"""


class DistributionSetEntry(object):
    """Cache entry in a distribution set.
    """

    def __init__(self, distribution_set, name):
        self.distribution_set = distribution_set
        self.name = name

    def resolve(self):
        """This resolves all dependencies, by finding corresponding
        releases.
        """

class DistributionSet(object):
    """Represent a possible set of releases that can be used together.
    """

    def __init__(self, source):
        self.source = source
        self.entries = {}
        self.requirements = Requirements()

    def search(self, name):
        pass


class Environment(object):
    """Represent the set of release used together.
    """

    def __init__(self, default_executable=None):
        self.installed = {}
        self.default_executable = default_executable
        self.source = None

        if self.default_executable == sys.executable:
            for path in sys.path:
                if os.path.isdir(os.path.join(path, 'EGG-INFO')):
                    self.add(EggRelease(path))

    def set_source(self, source):
        """Set the source used to find new software.
        """
        self.source = source

    def install(self, name, directory):
        # XXX Testing
        package = self.source.install(Requirement.parse(name), directory)
        print package.releases

    def add(self, release):
        """Try to add a new release in the environment.
        """
        if not isinstance(release, Release):
            import pdb ; pdb.set_trace()
            raise ValueError(u'Can only add release to an environment')
        if release.name not in self.installed:
            # XXX look for requires
            self.installed[release.name] = release
        else:
            installed = self.installed[release.name]
            if installed.path == release.path:
                self.installed[release.name] = release
            else:
                raise InstallationError(
                    u'Release %s and %s added in the environment' % (
                        repr(release), repr(self.installed[release.name])))

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

    def create_script(self, script_path, script_body, executable=None):
        """Create a script at the given path with the given body.
        """
        if executable is None:
            executable = self.default_executable
        logger.warning('Creating script %s' % script_path)
        modules_path = StringIO()
        printer = pprint.PrettyPrinter(stream=modules_path, indent=2)
        printer.pprint(map(lambda r: r.path, self.installed.values()))
        script_fd = open(script_path, 'w')
        script_fd.write(SCRIPT_TEMPLATE % {
                'executable': executable,
                'modules_path': modules_path.getvalue(),
                'script': script_body})
        script_fd.close()
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
        return script_path
