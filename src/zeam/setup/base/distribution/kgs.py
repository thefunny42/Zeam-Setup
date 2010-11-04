
import operator
import logging

from zeam.setup.base.version import Version, Requirement, Requirements

logger = logging.getLogger('zeam.setup')


class KnownGoodRequirementSet(object):

    def __init__(self, kgs):
        self.kgs = kgs
        self.available = set(kgs.registered())
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

    def __init__(self, options):
        self.options = options
        self.name = options.name.split(':', 1)[1]

    def requirements(self):
        return KnownGoodRequirementSet(self)

    def registered(self):
        return self.options.options.keys()

    def get(self, name):
        __status__ = u"Looking version for %s in Known Good Set %s." % (
            name, self.name)
        if name not in self.options:
            return None
        return Version.parse(self.options[name].as_text())
