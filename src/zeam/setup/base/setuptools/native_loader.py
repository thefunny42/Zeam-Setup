
import logging
import os
import shutil

from zeam.setup.base.egginfo.loader import EggLoader
from zeam.setup.base.error import PackageError


logger = logging.getLogger('zeam.setup')

def find_egg_info(distribution, base_path):
    """Go through a path to find an egg-info directory.
    """
    # We need to be case insensitif here as well.
    # Setuptools replace - with _ (why ?)
    wanted_directory = (distribution.name.replace('-', '_') +
                        '.egg-info').lower()
    for path, directories, filenames in os.walk(base_path):
        if wanted_directory in map(lambda s: s.lower(), directories):
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

        output, errors, code = self.execute(
            'bdist_egg', '-k', '--bdist-dir', install_path,
            path=self.distribution.package_path)
        if code:
            raise PackageError(
                u"Setuptools retuned status code %s, "
                u"while installing in %s." % (code, install_path),
                detail='\n'.join((output, errors)))


class NativeSetuptoolsLoaderFactory(object):
    """Load a setuptool source package.
    """

    def __init__(self, options):
        self.options = options
        self.setuptools_version = None
        self.setuptools_errors = False
        if options is not None:
            if 'setuptools_errors' in options:
                self.setuptools_errors = options['setuptools_errors'].as_bool()
            if 'setuptools_version' in options:
                self.setuptools_version = options['setuptools_version'].as_str()

    def __call__(self, distribution, path, interpretor, trust=-99):
        setup_py = os.path.join(path, 'setup.py')
        if os.path.isfile(setup_py):
            # You need to clean first the egg_info. install_requires
            # will trigger strange things only if it exists.
            egg_info_parent, egg_info = find_egg_info(distribution, path)
            if egg_info is not None and os.path.isdir(egg_info):
                # We will use the egg SOURCES.txt as input for a
                # MANIFEST. Most of packages miss one or have a
                # incomplete one and won't install everything without
                # one.
                if trust < 0:
                    source_file = os.path.join(egg_info, 'SOURCES.txt')
                    manifest_file = os.path.join(path, 'MANIFEST.in')
                    if os.path.isfile(source_file):
                        create_manifest_from_source(source_file, manifest_file)
                shutil.rmtree(egg_info)

            # Determine which version of setuptools to use
            execute = interpretor.execute_setuptools
            setuptools_version = None
            if distribution.name == 'setuptools':
                # To install setuptools, we need the same version.
                setuptools_version = str(distribution.version)
            else:
                setuptools_version = self.setuptools_version
            if setuptools_version is not None:

                def execute(*command, **options):
                    setuptools_options = {
                        'setuptools_version': setuptools_version}
                    setuptools_options.update(options)
                    return interpretor.execute_setuptools(
                        *command, **setuptools_options)

            # Get fresh egg_info
            output, errors, code = execute(
                'egg_info', path=path, setuptools_version=setuptools_version)
            if not code:
                egg_info_parent, egg_info = find_egg_info(distribution, path)
                if egg_info is not None and os.path.isdir(egg_info):
                    return NativeSetuptoolsLoader(
                        path, egg_info, distribution,
                        source_path=egg_info_parent, execute=execute)
                else:
                    logger.debug(
                        u"Could not find egg-info in  %s, " % (path))
            elif self.setuptools_errors:
                raise PackageError(
                    u"Setuptools retuned status code %s in  %s, " % (
                        code, path),
                    detail='\n'.join((output, errors)))
            else:
                logger.info(
                    u"Setuptools retuned status code %s in  %s, " % (
                        code, path))
        return None

