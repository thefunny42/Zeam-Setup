
import operator
import logging

from zeam.setup.base.version import Version, Requirement, Requirements
from zeam.setup.base.error import ConfigurationError

logger = logging.getLogger('zeam.setup')


class KnownGoodVersionSet(object):
    """Represent a Known Good Version set. Such a set can extends a
    another defined set.
    """

    def __init__(self, versions, extends=None):
        self.versions = versions
        self.name = versions.name.split(':', 1)[1]
        self.extends = extends
        self.used = set()
        self.missing = Requirements()

    def registered(self):
        registered = set(self.versions.options.keys())
        if self.extends is not None:
            registered = registered.union(self.extends.registered())
        return registered

    def get(self, name):
        __status__ = u"Looking version for %s in Known Good Set %s." % (
            name, self.name)
        if name not in self.versions:
            if self.extends is not None:
                return self.extends.get(name)
            return None
        self.used.add(name)
        return Version.parse(self.versions[name].as_text())

    def upgrade(self, requirement):
        __status__ = u"Restraining version to the known good set %s." % (
            self.name)
        name = requirement.name
        wanted = self.get(name)
        if wanted is None:
            self.missing.append(requirement)
            return requirement
        requirement += Requirement(name, [(operator.eq, wanted)])
        return requirement

    def unused(self):
        return sorted(set(self.versions.keys()) - self.used)

    def log_usage(self):
        if self.missing:
            for requirement in self.missing:
                logger.warn(
                    u"Missing requirement for %s in version set '%s'." % (
                        requirement, self.name))

        unused = self.unused()
        if unused:
            for name in unused:
                logger.info(
                    u"Unused requirement %s in version set '%s'." % (
                        name, self.name))
        if self.extends is not None:
            self.extends.log_usage()


def get_kgs_requirements(section):
    """Return a Known Good requirement set out of a configuration.
    """
    kgs = None
    names = section.get_with_default('versions', 'setup', '').as_list()
    if names:
        configuration = section.configuration
        for name in reversed(names):
            name = 'versions:' + name
            if name not in configuration:
                raise ConfigurationError(
                    u"Missing version set definition %s" % (name))
            kgs = KnownGoodVersionSet(configuration[name], kgs)
    return kgs
