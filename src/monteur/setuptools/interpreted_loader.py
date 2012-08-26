
import os
import logging

from monteur.configuration import Configuration
from monteur.python import PythonInterpreter
from monteur.setuptools.autotools import create_autotools
from monteur.setuptools import unsetuptoolize
from monteur.version import Version, Requirements

logger = logging.getLogger('monteur')


class InterpretedSetuptoolsLoader(object):

    def __init__(self, path, source):
        self.path = path
        self.source = source

    def extensions(self, prefix, section):
        __status__ = u"Introspecting distutils/setuptools extensions."
        extensions = []
        configuration = section.configuration
        for name in section['ext_modules'].as_list():
            ext_section =  configuration[name]
            if 'name' in ext_section:
                name = ext_section['name'].as_text()
                sources = ext_section['sources'].as_list()
            else:
                args_section = configuration[name + ':args']
                args = args_section['_'].as_list()
                # we can get as args name, or name and source.
                if len(args) > 1:
                    name, sources = args
                    sources = map(lambda s: s.strip(), sources.split(','))
                else:
                    name = args[0]
                    sources = ext_section['sources'].as_list()
            name = name.replace('.', '/')
            if prefix:
                name = '/'.join((prefix, name))
            depends = []
            if 'depends' in ext_section:
                depends = ext_section['depends'].as_list()
            libraries = []
            if 'libraries' in ext_section:
                libraries = ext_section['libraries'].as_list()
            paths = []
            if 'library_dirs' in ext_section:
                paths = ext_section['library_dirs'].as_list()
            includes = []
            if 'include_dirs' in ext_section:
                includes = ext_section['include_dirs'].as_list()
            macros = {}
            if 'define_macros' in ext_section:
                for macro in ext_section['define_macros'].as_list():
                    key, value = map(lambda s: s.strip(), macro.split(',', 1))
                    macros[key] = value
            extensions.append({'name':  name,
                              'sources': sources,
                              'macros': macros,
                              'depends': depends,
                              'paths': paths,
                              'libraries': libraries,
                              'includes': includes})
        return extensions

    def load(self, distribution, interpretor):
        distribution.package_path = self.path

        # Read extracted configuration
        config = Configuration.read_lines(self.source.splitlines, self.path)
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
        if 'description' in setuptool_config:
            distribution.description = setuptool_config['description'].as_text()
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

    def install(self, install_path):
        raise NotImplementedError


class InterpretedSetuptoolsLoaderFactory(object):
    """Load a setuptool source package.
    """

    def __call__(self, distribution, path, interpreter):
        setup_py = os.path.join(path, 'setup.py')
        if os.path.isfile(setup_py):
            interpretor = PythonInterpreter.detect()
            # XXX Review this
            source, _, code = interpretor.execute_module(
                unsetuptoolize, '-d', path)
            if not code:
                if source:
                    return InterpretedSetuptoolsLoader(path, source)
            logger.debug(u"Missing setuptools configuration in  %s, " % path)
        return None
