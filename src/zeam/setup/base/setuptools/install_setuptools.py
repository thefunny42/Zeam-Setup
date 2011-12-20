

if __name__ == '__main__':
    # Because we are crasy, we make a script to install setuptools in
    # a directory.
    import sys
    from ez_setup import download_setuptools
    try:
        download_setuptools(to_dir=sys.argv[1], delay=0)
    except:
        sys.exit(-1)
    sys.exit(0)

