
import operator
import logging

from zeam.setup.base.version import Version, Requirement, Requirements
from zeam.setup.base.error import ConfigurationError

logger = logging.getLogger('zeam.setup')


class KnownGoodVersionSet(object):
    """Represent a Known Good Version set.
    """

    def __init__(self, versions):
        self.versions = versions
        self.name = versions.name.split(':', 1)[1]
        self.used = set()
        self.missing = Requirements()

    def get(self, name):
        __status__ = u"Looking version for %s in Known Good Set %s." % (
            name, self.name)
        if name not in self.versions:
            return None
        self.used.add(name)
        return Version.parse(self.versions[name].as_text())

    def report_missing(self, requirement):
        self.missing.append(requirement)

    def log_usage(self):
        if self.missing:
            for requirement in self.missing:
                logger.warn(
                    u"Missing requirement for %s in version set '%s'." % (
                        requirement, self.name))

        unused = sorted(set(self.versions.keys()) - self.used)
        if unused:
            for name in unused:
                logger.info(
                    u"Unused requirement %s in version set '%s'." % (
                        name, self.name))


class KnownGoodVersionSetLookup(object):
    """Look in multiple KGS for a version.
    """

    def __init__(self, kgs):
        assert len(kgs) > 0
        self.kgs = kgs
        self.main = kgs[0]

    def get(self, name):
        for kgs in self.kgs:
            version = kgs.get(name)
            if version is not None:
                return version
        return None

    def upgrade(self, requirement):
        __status__ = u"Restraining version of %s to the known good set." % (
            requirement.name)
        name = requirement.name
        wanted = self.get(name)
        if wanted is None:
            self.main.report_missing(requirement)
            return requirement
        requirement += Requirement(name, [(operator.eq, wanted)])
        return requirement


class KGS(object):
    """Manage the existing KGS.
    """

    def __init__(self, configuration):
        self.configuration = configuration
        self.existing = {}
        # When we are done, we want to log KGS usage.
        configuration.utilities.atexit.register(self.log_usage)

    def lookup(self, name):
        """Lookup a unique KGS entry in the configuration.
        """
        if name not in self.existing:
            name = 'versions:' + name
            if name not in self.configuration:
                raise ConfigurationError(
                    u"Missing version set definition %s" % (name))
            self.existing[name] = KnownGoodVersionSet(self.configuration[name])
        return self.existing[name]

    def get(self, section):
        """Return a Known Good requirement set out of a configuration.
        """
        names = section.get_with_default('versions', 'setup', '').as_list()
        if names:
            return KnownGoodVersionSetLookup(map(self.lookup, names))
        return None

    def log_usage(self):
        """Log used and unused requirements.
        """
        names = self.existing.keys()
        names.sort()
        for name in names:
            self.existing[name].log_usage()
