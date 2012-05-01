
import os

from zeam.setup.base.error import ConfigurationError
from zeam.setup.base.utils import open_uri


def parse_manifest(manifest_name):
    """Read the given manifest file to give a dictionary of rules
    describing which files to include.
    """
    manifest = open_uri(manifest_name)
    regular_rules = {}
    recursive_rules = {}
    line_number = 0
    for text in manifest.readlines():
        line_number += 1
        # Comment
        if not text.strip() or text[0] in '#;':
            continue

        def manifest_current_location():
            manifest.close()
            return u'%s at line %d' % (manifest_name, line_number)

        parts = [t.strip() for t in text.split()]
        command = parts[0].lower()
        if command == 'include':
            if len(parts) < 2:
                raise ConfigurationError(
                    manifest_current_location(),
                    u"Malformed include directive")
            for part in parts[1:]:
                dirname = os.path.dirname(part)
                if not dirname:
                    dirname = './'
                else:
                    dirname = os.path.normpath(dirname) + os.path.sep
                rule = regular_rules.setdefault(dirname, list())
                rule.append(os.path.basename(part))
        elif command == 'recursive-include':
            if len(parts) < 3:
                raise ConfigurationError(
                    manifest_current_location(),
                    u"Malformed recursive-include directive")
            dirname = os.path.normpath(parts[1]) + os.path.sep
            rule = recursive_rules.setdefault(dirname, list())
            rule.extend(parts[2:])
        else:
            raise ConfigurationError(
                manifest_current_location(),
                u"Unknow manifest directive %s" % command)
    manifest.close()
    return (regular_rules, recursive_rules,)

