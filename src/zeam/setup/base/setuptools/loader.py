
import os
import logging

from zeam.setup.base.configuration import Configuration
from zeam.setup.base.setuptools.autotools import create_autotools
from zeam.setup.base.setuptools import unsetuptoolize
from zeam.setup.base.version import Version, Requirements

logger = logging.getLogger('zeam.setup')


class SetuptoolsLoader(object):

    def __init__(self, path):
        self.path = path

    def extensions(self, prefix, section):
        libraries = []
        configuration = section.configuration
        for name in section['ext_modules'].as_list():
            if name not in configuration:
                continue
            ext_section =  configuration[name]
            if 'name' in ext_section:
                name = ext_section['name'].as_text()
                sources = ext_section['sources'].as_list()
            else:
                args_section = configuration[name + ':args']
                name, sources = args_section['_'].as_list()
                sources = map(lambda s: s.strip(), sources.split(','))
            name = name.replace('.', '/')
            if prefix:
                name = '/'.join((prefix, name))
            depends = []
            if 'depends' in ext_section:
                depends = ext_section['depends'].as_list()
            includes = []
            if 'include_dirs' in ext_section:
                includes = ext_section['include_dirs'].as_list()
            macros = {}
            if 'define_macros' in ext_section:
                for macro in ext_section['define_macros'].as_list():
                    key, value = map(lambda s: s.strip(), macro.split(',', 1))
                    macros[key] = value
            libraries.append({'name':  name,
                              'sources': sources,
                              'macros': macros,
                              'depends': depends,
                              'includes': includes})
        return libraries

    def load(self, distribution, interpretor):
        # We must have a setuptool package. Extract information if possible
        # XXX this should move to available
        source = interpretor.execute(unsetuptoolize, '-d', self.path)
        if not source:
            logger.error(
                u"Missing setuptools configuration in %s, "
                u"giving up" % self.path)
            return None
        distribution.package_path = self.path

        # Read extracted configuration
        config = Configuration.read_lines(source.splitlines, self.path)
        setuptool_config = config['setuptools']
        distribution.version = Version.parse(
            setuptool_config['version'].as_text())

        # Look for requirements
        if 'install_requires' in setuptool_config:
            distribution.requirements = Requirements.parse(
                setuptool_config['install_requires'].as_list())
        if 'extras_require' in setuptool_config:
            extra_config = config[setuptool_config['extras_require'].as_text()]
            for extra, extra_requirements in extra_config.items():
                distribution.extras[extra] = Requirements.parse(
                    extra_requirements.as_list())

        # Look for source directory
        if 'package_dir' in setuptool_config:
            package_config = config[
                setuptool_config['package_dir'].as_text()]
            if '_' in package_config:
                prefix = package_config['_'].as_text()
                distribution.path = os.path.join(self.path, prefix)
        if 'license' in setuptool_config:
            distribution.license = setuptool_config['license'].as_text()
        if 'author' in setuptool_config:
            distribution.author = setuptool_config['author'].as_text()
        if 'autor_email' in setuptool_config:
            distribution.author_email = \
                setuptool_config['author_email'].as_text()
        if 'ext_modules' in setuptool_config:
            libraries = self.extensions(prefix, setuptool_config)
            create_autotools(distribution, prefix, libraries)
            distribution.extensions = libraries
        return distribution


class SetuptoolsLoaderFactory(object):

    def available(self, path):
        setup_py = os.path.join(path, 'setup.py')
        if os.path.isfile(setup_py):
            return SetuptoolsLoader(path)
        return None
