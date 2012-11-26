#!/usr/bin/env python2.7

import optparse
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib2

BASE_URL='https://github.com/thefunny42/Zeam-Setup/tarball/'
PREFIX='.monteur'
VERSION='0.1b6'

# Helper directories

def get_root(archive):
    for member in archive.getmembers():
        if member.isdir() and '/' not in member.name:
            return member.name
    return '.'

def create_directory(prefix_directory, directory=None):
    if directory is not None:
        prefix_directory = os.path.join(prefix_directory, directory)
    if not os.path.isdir(prefix_directory):
        os.makedirs(prefix_directory)
    return prefix_directory

def monteur_directory():
    return create_directory(os.getcwd(), PREFIX)

# Download an install methods

def download(version=VERSION):
    print 'Downloading monteur %s...' % VERSION
    download_dir = create_directory(monteur_directory(), 'download')
    tarball_file = os.path.join(download_dir, 'monteur-' + VERSION + '.tar.gz')
    if not os.path.isfile(tarball_file):
        try:
            data = urllib2.urlopen(BASE_URL + version)
            tmp_file = tempfile.mkstemp('zeam.setup.bootstrap')[1]
            stream = open(tmp_file, 'w')
            stream.write(data.read())
            stream.close()
            shutil.copy2(tmp_file, tarball_file)
            os.unlink(tmp_file)
        except:
            print 'Error while downloading monteur.'
            sys.exit(1)
    return tarball_file


def install(tarball_file):
    print 'Bootstraping monteur...'
    tmp_build = tempfile.mkdtemp('zeam.setup.bootstrap')
    try:
        archive = tarfile.open(tarball_file, 'r|gz')
        archive.extractall(tmp_build)
    except:
        print 'Error while extracting monteur.'
        sys.exit(1)

    bin_directory = create_directory(os.getcwd(), 'bin')
    lib_directory = create_directory(monteur_directory(), 'lib')
    # Run installation command
    command = subprocess.Popen(
        [sys.executable, 'bootstrap.py',
         '--option', 'bin_directory=' + bin_directory,
         '--option', 'lib_directory=' + lib_directory,
         '--option', 'source:vcs:develop=off'],
        cwd=os.path.join(tmp_build, get_root(archive)))
    command.communicate()


def bootstrap(version=VERSION):
    parser = optparse.OptionParser(usage='python bootstrap.py')
    parser.add_option(
        '--version', dest="version", default=VERSION,
        help="version of Monteur to install")
    options, args = parser.parse_args()
    install(download(options.version))


if __name__ == "__main__":
    bootstrap()
