
import operator
import logging

from zeam.setup.base.version import Version, Requirement, Requirements
from zeam.setup.base.error import ConfigurationError

logger = logging.getLogger('zeam.setup')


class KnownGoodVersionSet(object):
    """Represent a Known Good Version set.
    """

    def __init__(self, versions, installed_versions=None):
        self.versions = versions
        self.name = versions.name.split(':', 1)[1]
        self.used = set()
        self.missing = Requirements()
        self.installed_versions = installed_versions
        self._uptodate = None
        self._activated = False

    def get(self, name):
        if self._activated:
            __status__ = u"Looking version for %s in Known Good Set %s." % (
                name, self.name)
            if name in self.versions:
                self.used.add(name)
                return Version.parse(self.versions[name].as_text())
        return None

    def is_activated(self):
        return self._activated

    def is_uptodate(self):
        if self._uptodate is None:
            if self.installed_versions is None:
                self._uptodate = True
            else:
                self._uptodate = (self.versions == self.installed_versions)
        return self._uptodate

    def activate(self):
        # This means the KGS is activated in order to be used.
        self._activated = True

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


class KnownGoodVersionSetChain(object):
    """Look in multiple KGS for a version.
    """

    def __init__(self, kgs):
        assert len(kgs) > 0
        self.kgs = kgs
        self.main = kgs[0]

    def activate(self):
        for kgs in self.kgs:
            kgs.activate()

    def is_uptodate(self):
        return reduce(operator.and_, map(lambda k: k.is_uptodate(), self.kgs))

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
        self.installed = self.configuration.utilities.installed
        self.existing = {}
        # When we are done, we want to log KGS usage.
        configuration.utilities.atexit.register(self.log_usage)

    def lookup_kgs(self, name):
        """Lookup a unique KGS entry in the configuration.
        """
        if name not in self.existing:
            name = 'versions:' + name
            if name not in self.configuration:
                raise ConfigurationError(
                    u"Missing version set definition %s" % (name))
            self.existing[name] = KnownGoodVersionSet(
                self.configuration[name],
                self.installed.get(name, None))
        return self.existing[name]

    def lookup_chain(self, section):
        """Lookup a KGS chain in the configuration.
        """
        names = section.get_with_default('versions', 'setup', '').as_list()
        if names:
            return KnownGoodVersionSetChain(map(self.lookup_kgs, names))
        return None

    def get(self, section):
        """Return a Known Good requirement set out of a configuration.
        """
        kgs = self.lookup_chain(section)
        if kgs is not None:
            kgs.activate()
        return kgs

    def is_uptodate(self, section):
        """Return True if the KGS didn't change.
        """
        kgs = self.lookup_chain(section)
        if kgs is not None:
            return kgs.is_uptodate()
        return True

    def log_usage(self):
        """Log used and unused requirements.
        """
        names = self.existing.keys()
        names.sort()
        for name in names:
            kgs = self.existing[name]
            if kgs.is_activated():
                kgs.log_usage()

