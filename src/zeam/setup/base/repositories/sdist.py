
import fnmatch
import logging
import os

from zeam.setup.base.archives import ARCHIVE_MANAGER
from zeam.setup.base.error import PackageError, ConfigurationError
from zeam.setup.base.utils import open_uri

logger = logging.getLogger('zeam.setup')

DEFAULT_MANIFEST = os.path.join(os.path.dirname(__file__), 'MANIFEST.in')


def get_archive_manager(config, filename, mode):
    """Create an archive manager for correct selected format selected
    in the configuration.
    """
    format = config['setup']['archive_format'].as_text()
    if format not in ARCHIVE_MANAGER.keys():
        raise PackageError(u"Unknow package format %s" % format)
    return ARCHIVE_MANAGER[format]('.'.join((filename, format,),), mode)


def parse_manifest(manifest, manifest_name):
    """Read the given manifest file to give a dictionary of rules
    describing which files to include.
    """
    regular_rules = {}
    recursive_rules = {}
    line_number = 0
    for text in manifest.readlines():
        line_number += 1
        # Comment
        if not text.strip() or text[0] in '#;':
            continue

        def manifest_current_location():
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
    return (regular_rules, recursive_rules,)


def search_files(base_path, regular_rules, recursive_rules):
    """Search files in the given base_path matching the rules. This
    return the relative path from base_path.
    """

    def visit_directory(path):
        match_path = path + os.path.sep
        local_rules = list(regular_rules.get(match_path, []))
        for rule_path, rules in recursive_rules.items():
            if match_path.startswith(rule_path):
                local_rules.extend(rules)
        if local_rules:
            full_path = os.path.join(base_path, path)
            for entry in os.listdir(full_path):
                entry_path = os.path.join(full_path, entry)
                if os.path.isfile(entry_path):
                    for rule in local_rules:
                        if fnmatch.fnmatch(entry, rule):
                            yield os.path.normpath(os.path.join(path, entry))
                elif os.path.isdir(entry_path):
                    entries = visit_directory(os.path.join(path, entry))
                    for entry in entries:
                        yield entry

    return visit_directory('.')


class SourceDistribution(object):
    """Create a source distribution of the package
    """

    def __init__(self, session):
        self.configuration = session.configuration
        self.package = self.configuration.utilities.package
        self.prefix = self.configuration['setup']['prefix_directory'].as_text()

    def manifest(self):
        manifest_name = DEFAULT_MANIFEST
        egginfo = self.configuration['egginfo']
        if 'manifest' in egginfo:
            manifest_name = os.path.join(
                self.prefix, egginfo['manifest'].as_text())
        manifest = open_uri(manifest_name)
        # Do manifest stuff
        files = search_files(
            self.prefix, *parse_manifest(manifest, manifest_name))
        manifest.close()
        return files

    def run(self):
        basename = '%s-%s' % (self.package.name, self.package.version)
        archive = get_archive_manager(self.configuration, basename, 'w')
        logger.info(u'Creating %s.', archive.filename)
        for filename in self.manifest():
            logger.debug(u'Adding file %s.', filename)
            archive.add(
                os.path.join(self.prefix, filename),
                os.path.join(basename, filename))
        archive.close()
        return False
