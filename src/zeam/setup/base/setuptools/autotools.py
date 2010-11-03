
import os

CONFIGURE_AC_TEMPLATE = """
AC_PREREQ(2.55)
AC_INIT(%(project_name)s, %(project_version)s, thefunny@gmail.com)
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

def create_makefile_am(working_dir, makefile_dir, sub_dirs, libraries):
    makefile_path = os.path.join(working_dir, makefile_dir, 'Makefile.am')
    makefile = open(makefile_path, 'w')
    if makefile_dir in sub_dirs:
        makefile.write("SUBDIRS = %s\n\n" % ' '.join(sub_dirs[makefile_dir]))
    if makefile_dir in libraries:
        for library in libraries:
            name = os.path.basename(library['name'])
            makefile.write("%s_SOURCES = %s\n" % library)
    makefile.close()


def create_autotools(distribution, source_prefix, extensions):
    makefiles = []
    libraries = {}
    sub_dirs = {}
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

    configure_ac = open(os.path.join(
            distribution.package_path, 'configure.ac'), 'w')
    configure_ac.write(CONFIGURE_AC_TEMPLATE % configure_info)
    configure_ac.close()



