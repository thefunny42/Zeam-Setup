
import logging
import os
import urllib2
import urlparse

try:
    from hashlib import md5 as md5_sum
except ImportError:
    from md5 import new as md5_sum

from monteur.error import DownloadError
from monteur.utils import is_remote_uri

logger = logging.getLogger('monteur')

CHUNK_SIZE = 1024*1024


def get_checksum(url_parts):
    """Return the MD5 checksum of a file, when it is in the fragment:

    url#md5=checksum.
    """
    fragment = url_parts[-1]
    if '=' in fragment:
        name, value = fragment.split('=', 1)
        if name == 'md5':
            return value
    return None


def verify_checksum(path, checksum):
    """Verify that the file pointed by path is a file and verify the
    given MD5 checksum.
    """
    if not os.path.isfile(path):
        raise DownloadError(u"Donwloaded file is not a file.")
    if not checksum:
        # We don't have a checksum in fact
        return True
    input = open(path, 'r')
    hasher = md5_sum()
    buffer = input.read(CHUNK_SIZE)
    while buffer:
        hasher.update(buffer)
        buffer = input.read(CHUNK_SIZE)
    computed_checksum = hasher.hexdigest()
    is_valid = computed_checksum == checksum
    if not is_valid:
        logger.info("Checksum %s mismatch expected %s." % (
                computed_checksum, checksum))
    else:
        logger.debug("Checksum %s valid for %s" % (checksum, path))
    return is_valid


class DownloadManager(object):
    """Download files from da internet.
    """

    def __init__(self, directory):
        self.directory =  directory

    def __call__(self, uri):
        if is_remote_uri(uri):
            return self.download(uri)
        return uri

    def download(self, url, ignore_content_types=[]):
        """Download if not already there the file at the given URL
        into the directory. If the link includes an md5 checksum, it
        is compaired with the one obtained on the downloaded file.
        """
        __status__ = u"Downloading %s" % url
        url_parts = urlparse.urlparse(url)
        checksum = get_checksum(url_parts)
        base_filename = os.path.basename(url_parts[2])
        target_path = os.path.join(self.directory, base_filename)

        if os.path.exists(target_path):
            if verify_checksum(target_path, checksum):
                logger.info(u"File %s is already downloaded." % base_filename)
                return target_path
            raise DownloadError(
                u"File %s is already downloaded but "\
                u"the checksum is different", base_filename)

        try:
            logger.info("Downloading %s into %s..." % (url, base_filename))
            request = urllib2.Request(url=url)
            response = urllib2.urlopen(request)
        except urllib2.URLError, e:
            raise DownloadError(
                u"Error while downloading the file", base_filename, str(e))
            return None

        if ignore_content_types:
            content_type = response.headers.get(
                'content-type', '').split(';')[0]
            if content_type in ignore_content_types:
                response.close()
                raise DownloadError(
                    u"Content-type mismatch, got %s:" % content_type,
                    base_filename)

        try:
            output = open(target_path, 'wb')
            buffer = response.read(CHUNK_SIZE)
            while buffer:
                output.write(buffer)
                buffer = response.read(CHUNK_SIZE)
            logger.info("Download of %s complete." % base_filename)
        except IOError, e:
            raise DownloadError(
                u"Error while saving the file", base_filename, str(e))
        finally:
            response.close()
            output.close()

        if not verify_checksum(target_path, checksum):
            raise DownloadError(
                u"File %s is downloaded but the checksum is different",
                base_filename)
        return target_path
