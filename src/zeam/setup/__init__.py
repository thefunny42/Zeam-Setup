# this directory is a package
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)
