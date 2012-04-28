
import operator
import logging

from zeam.setup.base.version import Version, Requirement, Requirements
from zeam.setup.base.error import ConfigurationError

logger = logging.getLogger('zeam.setup')


class KnownVersion(object):
    """Represent a known version.
    """

    def __init__(self, option):
        self.key = option.name.lower().replace('-', '_')
        self.name = option.name
        self.version = option.as_text()


class KnownGoodVersionSet(object):
    """Represent a Known Good Version set.
    """

    def __init__(self, options, installed_options=None):
        self.versions = dict(map(lambda v: (v.key, v),
                                 map(KnownVersion, options.values())))
        self.name = options.name.split(':', 1)[1]
        self.used = set()
        self.missing = Requirements()
        self.picked = {}
        self.options = options
        self.installed_options = installed_options
        self._uptodate = None
        self._activated = False

    def get(self, requirement):
        if self._activated:
            __status__ = u"Looking version for %s in Known Good Set %s." % (
                str(requirement), self.name)
            if requirement.key in self.versions:
                self.used.add(requirement.key)
                return Version.parse(self.versions[requirement.key].version)
        return None

    def is_activated(self):
        return self._activated

    def is_uptodate(self):
        if self._uptodate is None:
            if self.installed_options is None:
                self._uptodate = True
            else:
                self._uptodate = (self.options == self.installed_options)
        return self._uptodate

    def activate(self):
        # This means the KGS is activated in order to be used.
        self._activated = True

    def report_missing(self, requirement):
        self.missing.append(requirement)

    def report_picked(self, requirement, version):
        picked = self.picked.setdefault(requirement, [])
        picked.append(version)

    def log_usage(self):
        if self.missing:
            for requirement in self.missing:
                msg = u"Missing requirement for '%s' in '%s'"
                args = (requirement, self.name)
                picked = self.picked.get(requirement)
                if picked:
                    msg += u", picked '%s'"
                    args += (','.join(map(str, picked)),)
                msg += u"."
                logger.warn(msg, *args)

        unused = sorted(set(self.versions.keys()) - self.used)
        if unused:
            for name in unused:
                logger.info(
                    u"Unused requirement '%s' in '%s'.",
                    self.versions[name].name, self.name)


class KnownGoodVersionSetChain(object):
    """Look in multiple KGS for a version.
    """

    def __init__(self, kgs):
        assert len(kgs) > 0
        self.kgs = kgs
        main = kgs[0]
        self.report_missing = main.report_missing
        self.report_picked = main.report_picked

    def activate(self):
        for kgs in self.kgs:
            kgs.activate()

    def is_uptodate(self):
        return reduce(operator.and_, map(lambda k: k.is_uptodate(), self.kgs))

    def get(self, requirement):
        for kgs in self.kgs:
            version = kgs.get(requirement)
            if version is not None:
                return version
        return None

    def upgrade(self, requirement):
        __status__ = u"Restraining version of %s to the known good set." % (
            requirement.name)
        wanted = self.get(requirement)
        if wanted is None:
            self.report_missing(requirement)
            return requirement
        requirement += Requirement(requirement.name, [(operator.eq, wanted)])
        return requirement


class KGS(object):
    """Manage the existing KGS.
    """

    def __init__(self, configuration):
        self.configuration = configuration
        self.installed = self.configuration.utilities.installed
        self.existing = {}
        # When we are done, we want to log KGS usage.
        configuration.utilities.events.subscribe('finish', self.log_usage)

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

    def log_usage(self, *ignore):
        """Log used and unused requirements.
        """
        names = self.existing.keys()
        names.sort()
        for name in names:
            kgs = self.existing[name]
            if kgs.is_activated():
                kgs.log_usage()

