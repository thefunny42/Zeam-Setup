
from optparse import OptionParser
import ConfigParser
import os
import sys
import parser
import types

def export_setup(export_name, stream, increment_name=False):
    names = []
    def setup(*args, **kwargs):
        config = ConfigParser.ConfigParser()
        def serialize(name, data):
            config.add_section(name)
            for key, value in data.items():
                if not key:
                    key = '_'
                if isinstance(value, list):
                    value = '\n'.join(map(str, value))
                if isinstance(value, dict):
                    sub_name = 'section:' + key
                    config.set(name, key, sub_name)
                    serialize(sub_name, value)
                else:
                    config.set(name, key, value)

        name = export_name
        if increment_name:
            name += ':%d' % len(names)
            names.append(name)
        serialize(name, kwargs)
        if args:
            serialize(name + ':args', {'args': args})
        config.write(stream)
        return name
    return setup


def find_packages(*args, **kwargs):
    return []


def unsetuptoolize(filename='setup.py'):
    opt_parser  = OptionParser()
    opt_parser.add_option(
        "-d", "--directory", dest="directory",
        help="switch to the given directory before processing")

    (options, args) = opt_parser.parse_args()

    sys.argv = [filename]
    if options.directory:
        directory = os.path.abspath(options.directory)
        sys.path.append(directory)
        os.chdir(directory)
        filename = os.path.join(directory, filename)

    # Redirect output somewhere
    config_out = os.fdopen(os.dup(1), 'w')
    script_out = os.tmpfile()
    script_err = os.tmpfile()
    os.dup2(script_out.fileno(), 1)
    os.dup2(script_err.fileno(), 2)

    # Create a setuptool module to prevent to load it
    sys.modules['setuptools'] = types.ModuleType(
        'setuptools')
    sys.modules['setuptools.extension'] = types.ModuleType(
        'extension')

    # Register our setuptools fonctions.
    import setuptools
    setuptools.setup = export_setup('setuptools', config_out)
    setuptools.Extension = export_setup('extension', config_out, True)
    setuptools.Feature = export_setup('feature', config_out, True)
    setuptools.find_packages = find_packages
    setuptools.extension = sys.modules['setuptools.extension']
    setuptools.extension.Extension = export_setup('extension', config_out, True)

    # Load and execute the code that will call back our setup method.
    source_file = open(filename, 'r')
    source = "\ndef _unsetuptoolwrapper():\n"
    for line in source_file.readlines():
        source += "    " + line
    source += "\n\n_unsetuptoolwrapper()"
    source_file.close()
    code = parser.suite(source)
    globs = globals()
    globs['__doc__'] = "This package have been unsetuptooled by Zeam Corp"
    globs['__file__'] = filename
    success = True
    try:
        exec(code.compile(filename), globs, {})
    except:
        success = False

    # Include script output and error output
    config = ConfigParser.ConfigParser()
    config.add_section('info')
    sys.stdout.flush()
    script_out.seek(0)
    config.set('info', 'stdout', script_out.read())
    sys.stderr.flush()
    script_err.seek(0)
    config.set('info', 'stderr', script_err.read())
    config.set('info', 'complete', success)
    config.write(config_out)

    sys.exit(0)


if __name__ == "__main__":
    unsetuptoolize()
