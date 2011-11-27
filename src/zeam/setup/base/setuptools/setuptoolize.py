
if __name__ == "__main__":
    # The first sys.path should be the current directory
    __import__('sys').path[0] = __import__('os').getcwd()
    # Load setuptools
    import setuptools
    # Load setup.py as __main__
    __import__('imp').load_source('__main__', 'setup.py')
