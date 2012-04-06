

if __name__ == '__main__':
    # Because we are crasy, we make a script to install setuptools in
    # a directory.
    import sys
    from ez_setup import download_setuptools, DEFAULT_VERSION
    version = DEFAULT_VERSION
    if len(sys.argv) == 3 and sys.argv[2] != 'default':
        version = sys.argv[2]
    target_dir = sys.argv[1]
    try:
        download_setuptools(version=version, to_dir=target_dir, delay=0)
    except:
        sys.exit(-1)
    sys.exit(0)

