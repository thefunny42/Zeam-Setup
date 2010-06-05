
import sys
import types
import ConfigParser
import parser


def setup(*args, **kwargs):
    if args:
        print "Invalid setuptools file: Arguments received."
        sys.exit(255)

    config = ConfigParser.ConfigParser()

    def serialize(name, data):
        config.add_section(name)
        for key, value in data.items():
            if isinstance(value, list):
                value = '\n'.join(value)
            if isinstance(value, dict):
                sub_name = 'section:' + key
                config.set(name, key, sub_name)
                serialize(sub_name, value)
            else:
                config.set(name, key, value)

    serialize('section:setuptools', kwargs)
    extracted_config = open('setuptool_config.cfg', 'w')
    config.write(extracted_config)
    extracted_config.close
    sys.exit(0)


def find_packages(*args, **kwargs):
    return []


def unsetuptoolize(filename='setup.py'):
    # Create a setuptool module to prevent to load it
    sys.modules['setuptools'] = types.ModuleType('setuptools')

    # Register our setuptools fonctions.
    import setuptools
    setuptools.setup = setup
    setuptools.find_packages = find_packages

    # Load and execute the code that will call back our setup method.
    source_file = open(filename, 'r')
    source = source_file.read()
    source_file.close()
    code = parser.suite(source)
    exec(code.compile(), {}, {})

    # We are still here, not a setuptool script
    sys.exit(1)

if __name__ == "__main__":
    unsetuptoolize()
