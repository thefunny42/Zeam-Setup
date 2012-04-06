
if __name__ == "__main__":
    import sys, os, imp
    # Load setuptools. Be sure we load it from the provided Python path.
    imp.load_module(
        'setuptools',
        *imp.find_module('setuptools', [os.environ['PYTHONPATH']]))
    # Add the current directory to sys.path, for pseudo clever scripts
    sys.path[0] = os.getcwd()
    # Some scripts try to be even clever.
    sys.argv[0] = os.path.join(os.getcwd(), 'setup.py')
    # Load setup.py as __main__
    __import__('imp').load_source('__main__', 'setup.py')
