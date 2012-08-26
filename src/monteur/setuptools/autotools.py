
import atexit
import logging
import operator
import os
import tempfile

from monteur.utils import get_cmd_output
from monteur.error import PackageError

logger = logging.getLogger('monteur')


CONFIGURE_AC_TEMPLATE = """
AC_PREREQ(2.55)
AC_INIT(%(project_name)s, %(project_version)s, thefunny@gmail.com)
AC_CONFIG_MACRO_DIR(m4)
AC_CONFIG_SRCDIR(%(source_prefix)s)
AM_CONFIG_HEADER(config.h)
AM_DISABLE_STATIC
AM_INIT_AUTOMAKE(1.10)
AC_LANG_C
AC_PROG_MAKE_SET
AC_PROG_LIBTOOL
AC_PROG_INSTALL
AM_PATH_PYTHON
AC_PYTHON_DEVEL
AC_CONFIG_FILES([%(makefiles)s])
AC_OUTPUT
"""
AUTOMAKE_OPTIONS = {'': """
AUTOMAKE_OPTIONS = 1.10 foreign
ACLOCAL_AMFLAGS=-I m4
"""}

def relative_path(path_orig, path_dest):
    """Takes two path as list of ids and return a new path that is the
    relative path the second against the first.
    """
    path_orig = path_orig.split(os.path.sep)
    path_dest = path_dest.split(os.path.sep)
    while ((path_orig and path_dest) and
           (path_orig[0] == path_dest[0])):
        path_orig.pop(0)
        path_dest.pop(0)
    result_path = ['..'] * len(path_orig)
    result_path.extend(path_dest)
    if not result_path:
        return '.'
    return os.path.join(*result_path)


def prefix_join(prefix, items):
    """Prefix all items and join them.
    """
    if items:
        return prefix + prefix.join(items)
    return ''


def create_makefile_am(
    working_dir, prefix_dir, makefile_dir, sub_dirs, libraries):
    """Create a Makefile.am from information.
    """
    makefile_sub_dirs = []
    makefile_path = os.path.join(working_dir, makefile_dir, 'Makefile.am')
    makefile = open(makefile_path, 'w')
    if makefile_dir in AUTOMAKE_OPTIONS:
        # Extra level options
        makefile.write(AUTOMAKE_OPTIONS[makefile_dir])

    if makefile_dir in sub_dirs:
        # Sub directories
        makefile_sub_dirs = sub_dirs[makefile_dir]
        makefile.write("SUBDIRS = %s\n\n" % ' '.join(makefile_sub_dirs))

    if makefile_dir in libraries:
        # Extensions
        makefile_libraries = libraries[makefile_dir]
        includes = ''
        for include in set(reduce(operator.add,
                                  map(operator.itemgetter('includes'),
                                      makefile_libraries))):
            if include[0] == os.path.sep:
                includes += ' -I' + include
            else:
                includes += ' -I${top_srcdir}/' + include
        makefile.write("INCLUDES =%s ${PYTHON_CPPFLAGS}\n\n" % includes)
        extension_dir = relative_path(prefix_dir, makefile_dir)
        makefile.write("extensiondir = ${prefix}/%s\n" % extension_dir)
        makefile.write(
            "extension_LTLIBRARIES = %s\n" % (
                '.la '.join(
                    map(os.path.basename,
                        map(operator.itemgetter('name'),
                            makefile_libraries))) + '.la'
                ))
        files = lambda l: ' '.join(
            map(lambda p: relative_path(makefile_dir, p), l))
        for library in makefile_libraries:
            name = os.path.basename(library['name'])
            makefile.write(
                "%s_la_SOURCES = %s\n" % (name, files(library['sources'])))
            if 'depends' in library and library['depends']:
                makefile.write(
                    "%s_la_DEPENDENCIES = %s\n" % (
                        name, files(library['depends'])))
            if 'macros' in library:
                macros = ''
                for key, value in library['macros'].items():
                    if value:
                        macros += ' -D%s=%s' % (key, value)
                    else:
                        macros += ' -D%s' % key
                makefile.write("%s_la_CPPFLAGS =%s\n" % (name, macros))
            if 'libraries' in library:
                makefile.write("%s_la_LIBADD =%s\n" % (
                        name, prefix_join(' -l', library['libraries'])))
            if 'paths' in library:
                makefile.write("%s_la_CFLAGS =%s\n" % (
                        name, prefix_join(' -L', library['paths'])))
            makefile.write(
                "%s_la_LDFLAGS = -module -avoid-version -shared\n" % name)
    makefile.close()

    for sub_dir in makefile_sub_dirs:
        # Create makefile for sub directories
        create_makefile_am(
            working_dir,
            prefix_dir,
            os.path.join(makefile_dir, sub_dir),
            sub_dirs,
            libraries)


def create_autotools(distribution, source_prefix, extensions):
    """Create an autotools installation into the given distribution to
    compile the described extensions.
    """
    makefiles = []
    libraries = {}
    sub_dirs = {}
    working_dir = distribution.package_path

    logger.info("Creating autotools installation in %s" % working_dir)

    for extension in extensions:
        path = os.path.dirname(extension['name'])
        makefile = os.path.join(path, 'Makefile')
        if makefile not in makefiles:
            makefiles.append(makefile)
        path_libraries = libraries.setdefault(path, [])
        path_libraries.append(extension)

    # We need to make sure we have all Makefile, even those with no
    # exntensions (only subdirs)
    for makefile in makefiles:
        parts = makefile.split(os.path.sep)
        for index in range(len(parts) - 1):
            sub_dir =  ''
            if index:
                sub_dir = os.path.join(*parts[:index])
            sub_makefile = os.path.join(sub_dir, 'Makefile')
            if sub_makefile not in makefiles:
                makefiles.append(sub_makefile)
            sub_dirs.setdefault(sub_dir, set()).add(parts[index])
    makefiles.sort()

    configure_info = {'project_name': distribution.name,
                      'project_version': distribution.version,
                      'source_prefix': source_prefix,
                      'makefiles': ' '.join(makefiles)}

    configure_ac = open(os.path.join(working_dir, 'configure.ac'), 'w')
    configure_ac.write(CONFIGURE_AC_TEMPLATE % configure_info)
    configure_ac.close()

    create_makefile_am(working_dir, source_prefix, '', sub_dirs, libraries)
    macros_dir = os.path.join(working_dir, 'm4')
    if not os.path.isdir(macros_dir):
        os.makedirs(macros_dir)
    python_m4 = os.path.join(os.path.dirname(__file__), 'python.m4')
    # XXX os.link doesn't work on windaube
    os.link(python_m4, os.path.join(macros_dir, 'python.m4'))

    stdout, stderr, code = get_cmd_output(
        'autoreconf', '-v', '-f', '-i', path=working_dir)
    if code:
        raise PackageError(u"Autotools creation failed in %s." % working_dir)



class AutomakeBuilder(object):

    def __init__(self):
        self.cache_name = tempfile.mkstemp('monteur.autotools.cache')[1]
        atexit.register(os.remove, self.cache_name)

    def build(self, distribution, path, interpretor):
        working_dir = distribution.package_path
        logger.info("Building extensions in %s" % working_dir)
        environ = {'PYTHON': str(interpretor)}
        stdout, stderr, code = get_cmd_output(
            'configure',
            '--prefix=%s' % path,
            '--cache-file=%s' % self.cache_name,
            path=working_dir, environ=environ, no_stdout=True)
        if code:
            raise PackageError(
                u"Extensions configuration failed for %s." % distribution)
        stdout, stderr, code = get_cmd_output(
            'make',
            path=working_dir, no_stdout=True)
        if code:
            raise PackageError(
                u"Extensions build failed for %s." % distribution)

    def install(self, distribution, path, interpretor):
        working_dir = distribution.package_path
        logger.info("Installing extensions from %s" % working_dir)
        stdout, stderr, code = get_cmd_output(
            'make',
            'install',
            path=working_dir, no_stdout=True)
        if code:
            raise PackageError(
                u"Extensions installation failed for %s." % distribution)


