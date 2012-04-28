
import os
import re
import logging
import tempfile
import shutil

from zeam.setup.base.archives import ARCHIVE_MANAGER
from zeam.setup.base.distribution.release import Release
from zeam.setup.base.error import PackageError
from zeam.setup.base.version import Version, InvalidVersion

logger = logging.getLogger('zeam.setup')
marker = object()



RELEASE_TARBALL = re.compile(
    r'^(?P<name>.*?)-(?P<version>[^-]*(-[\d]+)?(-[\w]+)*(-r[\d]+)?)'
    r'(-py(?P<pyversion>[\d.]+)(-(?P<platform>[\w\d_.-]+))?)?'
    r'\.(?P<format>zip|egg|tgz|tar\.gz)$',
    re.IGNORECASE)


def get_installer_from_name(source, link, url=None, path=None):
    """Return a not installed installer from the given name.
    """
    info = RELEASE_TARBALL.match(link)
    if info:
        try:
            name = info.group('name')
            version = Version.parse(info.group('version'))
            format = info.group('format')
            pyversion = info.group('pyversion')
            platform = info.group('platform')
            return source.factory(
                source,
                name=name, version=version, format=format, url=url, path=path,
                pyversion=pyversion, platform=platform)
        except InvalidVersion:
            logger.debug(
                u"Link to '%s' seems to be a package, "
                u"but can't make sense out of it, ignoring it." % link)
            return None
    return None


class PackageInstaller(object):
    """Install an already installed package: load informations and
    install dependencies.
    """

    def __init__(self, source, **informations):
        self.source = source
        self.trust = -99        # Level of trust of quality for the packaging.
        if 'trust' in informations:
            self.trust = informations['trust']
            del informations['trust']
        assert 'name' in informations
        informations.setdefault('version', None)
        self.informations = informations
        # Be compatible with setuptools rules.
        self.key = informations['name'].lower().replace('-', '_')

    def filter(self, requirement, pyversion=None, platform=None):
        if pyversion is not None and self.pyversion is not None:
            if pyversion != self.pyversion:
                return False
        if platform is not None and self.platform is not None:
            if platform != self.platform:
                return False
        return requirement.match(self)

    def __getattr__(self, key):
        if key in self.informations:
            return self.informations[key]
        raise AttributeError(key)

    def __lt__(self, other):
        return ((self.version, -self.source.priority) <
                (other.version, -other.source.priority))

    def __gt__(self, other):
        return ((self.version, self.source.priority) >
                (other.version, other.source.priority))

    def __eq__(self, other):
        return (self.version, self.platform) == (other.version, other.platform)

    def install(self, path, interpretor, install_dependencies):
        distribution = Release(**self.informations)
        loader = self.source.options.utilities.releases.load(
            distribution, distribution.path, interpretor, trust=self.trust)
        install_dependencies(distribution)
        return distribution, loader


class ExtractedPackageInstaller(PackageInstaller):
    """An extracted release that you can install.
    """

    def install(self, path, interpretor, install_dependencies):
        # Load project information
        distribution, loader = super(ExtractedPackageInstaller, self).install(
            path, interpretor, install_dependencies)

        # Install files
        install_path = os.path.join(
            path, distribution.get_egg_directory(interpretor))
        loader.install(install_path)

        # Package path is now the installed path
        distribution.path = install_path
        distribution.package_path = install_path
        return distribution, loader


class UninstalledPackageInstaller(ExtractedPackageInstaller):
    """A release that you can extract from an archive and install.
    """

    def install(self, path, interpretor, install_dependencies, archive=None):
        if archive is None:
            archive = self.informations['url']

        format = self.informations['format']
        factory = ARCHIVE_MANAGER.get(format, None)
        if factory is None:
            raise PackageError(
                u"Don't know how to read package file %s, " \
                u"unknown format %s." % (archive, format))
        extractor = factory(archive, 'r')
        build_dir = tempfile.mkdtemp('zeam.setup')
        extractor.extract(build_dir)

        # Archive name without extension, paying attention to .tar.gz
        # (so can't use os.path.splitext)
        source_path = os.path.basename(archive)[:-(len(format)+1)]
        source_path = os.path.join(build_dir, source_path)
        if not os.path.isdir(source_path):
            logger.debug(
                u"Non-standard archive for %s" % self.informations['name'])
            # Ok the folder has the same name than the archive. Try to
            # see if there is only one folder in the archive, ignore
            # what starts with .
            source_path = None
            candidate_paths = filter(os.path.isdir, map(
                    lambda p: os.path.join(build_dir, p),
                    filter(lambda s: s and s[0] != '.', os.listdir(build_dir))))
            if len(candidate_paths) == 1:
                # If there is only one directory in the archive use it.
                source_path = candidate_paths[0]
            if source_path is None:
                raise PackageError(
                    u"Cannot introspect archive content for %s" % (archive,))
        self.informations['path'] = source_path

        # Load project information
        distribution, loader = super(UninstalledPackageInstaller, self).install(
            path, interpretor, install_dependencies)

        # Clean build directory
        shutil.rmtree(build_dir)

        return distribution, loader


