
if __name__ == "__main__":
    import sys, os
    # The first sys.path should be the current directory
    sys.path[0] = os.getcwd()
    # Some scripts try to be clever.
    sys.argv[0] = os.path.join(os.getcwd(), 'setup.py')
    # Load setuptools
    import setuptools
    # Load setup.py as __main__
    __import__('imp').load_source('__main__', 'setup.py')
