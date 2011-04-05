
import operator
import logging

from zeam.setup.base.version import Version, Requirement, Requirements
from zeam.setup.base.error import ConfigurationError

logger = logging.getLogger('zeam.setup')


class KnownGoodRequirementSet(object):
    """Represent a Known Good Requirement set, created from a Known
    Good Version set.
    """

    def __init__(self, kgs):
        self.kgs = kgs
        self.available = kgs.registered()
        self.used = set()
        self.missing = Requirements()

    def upgrade(self, requirement):
        __status__ = u"Restraining version to the Known Good Set %s." % (
            self.kgs.name)
        name = requirement.name
        wanted_version = self.kgs.get(name)
        if wanted_version is None:
            self.missing.append(requirement)
            return requirement
        requirement += Requirement(name, [(operator.eq, wanted_version)])
        self.used.add(name)
        return requirement

    def unused(self):
        return list(self.available - self.used)

    def log_usage(self):
        if self.missing:
            for requirement in self.missing:
                logger.warning(
                    u'Missing requirement for %s in version set %s.' % (
                        requirement, self.kgs.name))

        unused = self.unused()
        if unused:
            for name in unused:
                logger.info(
                    u'Unused requirement description %s in version set %s.' % (
                        name, self.kgs.name))


class KnownGoodVersionSet(object):
    """Represent a Known Good Version set. Such a set can extends a
    another defined set.
    """

    def __init__(self, versions, extends_set=None):
        self.versions = versions
        self.name = versions.name.split(':', 1)[1]
        self.extends_set = extends_set

    def requirements(self):
        return KnownGoodRequirementSet(self)

    def registered(self):
        registered = set(self.versions.options.keys())
        if self.extends_set is not None:
            registered = registered.union(self.extends_set.registered())
        return registered

    def get(self, name):
        __status__ = u"Looking version for %s in Known Good Set %s." % (
            name, self.name)
        if name not in self.versions:
            if self.extends_set is not None:
                return self.extends_set.get(name)
            return None
        return Version.parse(self.versions[name].as_text())


def get_kgs_requirements(section_names, configuration):
    """Return a Known Good requirement set out of a configuration.
    """
    kgs = None
    for name in reversed(section_names):
        name = 'versions:' + name
        if name not in configuration:
            raise ConfigurationError(
                u"Missing version set definition %s" % (name))
        kgs = KnownGoodVersionSet(configuration[name], kgs)
    if kgs is None:
        raise ConfigurationError(u"Invalid empty version set")
    return kgs.requirements()
