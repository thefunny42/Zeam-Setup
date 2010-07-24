
from optparse import OptionParser
import ConfigParser
import os
import sys
import parser
import types


def setup(*args, **kwargs):
    if args:
        return

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

    serialize('setuptools', kwargs)
    config.write(sys.stdout)


def find_packages(*args, **kwargs):
    return []


def unsetuptoolize(filename='setup.py'):
    opt_parser  = OptionParser()
    opt_parser.add_option(
        "-d", "--directory", dest="directory",
        help="switch to the given directory before processing")

    (options, args) = opt_parser.parse_args()

    if options.directory:
        directory = os.path.abspath(options.directory)
        sys.path.append(directory)
        os.chdir(directory)
        filename = os.path.join(directory, filename)

    # Create a setuptool module to prevent to load it
    sys.modules['setuptools'] = types.ModuleType(
        'setuptools')
    sys.modules['setuptools.extension'] = types.ModuleType(
        'extension')

    # Register our setuptools fonctions.
    import setuptools
    setuptools.setup = setup
    setuptools.Extension = setup
    setuptools.Feature = setup
    setuptools.find_packages = find_packages
    setuptools.extension = sys.modules['setuptools.extension']
    setuptools.extension.Extension = setup

    # Load and execute the code that will call back our setup method.
    source_file = open(filename, 'r')
    source = "\ndef _unsetuptoolthatcrap():\n"
    for line in source_file.readlines():
        source += "    " + line
    source += "\n\n_unsetuptoolthatcrap()"
    source_file.close()
    code = parser.suite(source)
    globs = globals()
    globs['__doc__'] = "This package have been unsetuptooled"
    globs['__file__'] = filename
    exec(code.compile(filename), globs, {})

    # We are still here, not a setuptool script
    sys.exit(1)


if __name__ == "__main__":
    unsetuptoolize()
