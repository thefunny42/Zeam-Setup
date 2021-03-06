
import re
import operator

from monteur.error import PackageError

VERSION_PARTS = re.compile(r'(\d+|[a-z]+|\.|-)')
VERSION_REPLACE = {
    'alpha': 'a', 'beta': 'b', 'pre':'c', 'preview':'c', '-':'final-',
    'post': 'final-', 'rc':'c'}.get
REQUIREMENT_NAME_PARSE = re.compile(
    r'^(?P<name>[\w._-]+)\s*'
    r'(\[(?P<extras>[\w\s.,]+)\])?\s*'
    r'(?P<requirements>.*)$')
REQUIREMENT_VERSION_PARSE = re.compile(
    r'(?P<operator>[<>=!]=)\s*(?P<version>[\da-z.\-]+)\s*,?')
REQUIREMENT_TO_OPERATORS = {'==': operator.eq, '>=': operator.ge,
                            '!=': operator.ne, '<=': operator.le}.get
OPERATORS_TO_REQUIREMENT = {operator.eq: '==', operator.ge: '>=',
                            operator.ne: '!=', operator.le: '<='}.get


def keyify(name):
    """Return a software setuptools key from its name.
    """
    return name.lower().replace('-', '_')


class InvalidVersion(PackageError):
    """This version is invalid.
    """
    name = u'Invalid version'


class InvalidRequirement(ValueError):
    """Those requirement are invalids.
    """


class IncompatibleRequirement(PackageError):
    """This requirement is not compatible with a release or installer.
    """
    name = u'Incompatible requirement'

    def msg(self):
        requirement, release = self.args
        return u'%s: "%s" is not compatible with picked release "%s"' % (
            self.name, requirement, release)


class IncompatibleVersion(PackageError):
    """Those reauirement are not compatible together.
    """
    name = u'Incompatible requirement version'

    def msg(self):
        requirements = []
        for op, version in self.args[1:]:
            requirements.append(
                ' '.join((OPERATORS_TO_REQUIREMENT(op), str(version))))
        return ': '.join((self.name, self.args[0], ', '.join(requirements)))


class Version(object):
    """Represent a version of a software.
    """

    def __init__(self, *version):
        self.version = version

    @classmethod
    def parse(cls, version):
        if not version:
            return None
        if isinstance(version, cls):
            return version
        if version == 'latest':
            return cls('~', '*final')

        def split_version_in_parts():
            # This comes from setuptools
            for part in VERSION_PARTS.split(version.lower()):
                if not part or part == '.':
                    continue
                part = VERSION_REPLACE(part, part)
                if part[0] in '0123456789':
                    yield part.zfill(8)
                elif part != 'final':
                    yield '*' + part
            yield '*final'

        parsed_version = []
        for part in split_version_in_parts():
            if part.startswith('*'):
                if part < '*final':   # remove '-' before a prerelease tag
                    while parsed_version and parsed_version[-1] == '*final-':
                        parsed_version.pop()
                # normalize trailing zero to one
                if len(parsed_version) < 2:
                    if not len(parsed_version):
                        raise InvalidVersion(version)
                    parsed_version.append('00000000')
                else:
                    while (len(parsed_version) > 2
                           and parsed_version[-1] == '00000000'):
                        parsed_version.pop()
            parsed_version.append(part)
        return cls(*parsed_version)

    def __lt__(self, other):
        return self.version < other

    def __le__(self, other):
        return self.version <= other

    def __gt__(self, other):
        return self.version > other

    def __ge__(self, other):
        return self.version >= other

    def __eq__(self, other):
        return self.version == other

    def __ne__(self, other):
        return self.version != other

    def __str__(self):
        rendered_version = []
        need_dot = False
        for part in self.version[:-1]:
            if part == '~':
                rendered_version.append('latest')
            if part[0] == '*':
                if part == '*final-':
                    rendered_version.append('-')
                else:
                    rendered_version.append(part[1:])
            elif need_dot:
                rendered_version.append('.')
            need_dot = False
            if part[0] == '0':
                rendered_version.append(part.lstrip('0') or '0')
                need_dot = True
        return ''.join(rendered_version)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.__str__())



def reduce_requirements(name, *reqs):
    """Reduce a list of version requirements to a shorter one if possible.
    """
    # XXX there is probably a way to do it better.
    new_reqs = []
    consume_reqs = reduce(operator.add, reqs)
    while len(consume_reqs):
        current = consume_reqs.pop()
        op, version = current
        keep_current = True

        def reduce_reqs(other_reqs):
            keep_req = True
            for index, other in enumerate(other_reqs):
                other_op, other_version = other

                if op is operator.eq:
                    if other_op is operator.eq:
                        # check for other eq, version == remove self, else error
                        if other_version == version:
                            del other_reqs[index]
                        else:
                            raise IncompatibleVersion(name, current, other)
                    elif other_op is operator.ne:
                        # check if != version == error else remove
                        if other_version == version:
                            raise IncompatibleVersion(name, current, other)
                        else:
                            del other_reqs[index]
                    elif other_op is operator.le:
                        # check if version is in range
                        if other_version < version:
                            raise IncompatibleVersion(name, current, other)
                        else:
                            del other_reqs[index]
                    elif other_op is operator.ge:
                        # check if version is in range
                        if other_version > version:
                            raise IncompatibleVersion(name, current, other)
                        else:
                            del other_reqs[index]

                elif op is operator.ge:
                    # check for other ge, version >= remove it else remove self
                    if other_op is operator.ge:
                        if version > other_version:
                            del other_reqs[index]
                        else:
                            keep_req = False
                    # check for other le, version <= error
                    elif other_op is operator.le:
                        if other_version < version:
                            raise IncompatibleVersion(name, current, other)
                    # check for eq not in range
                    elif other_op is operator.eq:
                        if other_version < version:
                            raise IncompatibleVersion(name, current, other)
                    # check for neq in range or remove it
                    elif other_op is operator.ne:
                        if other_version < version:
                            del other_reqs[index]

                elif op is operator.le:
                    # check for other le, version <= remove it else remove self
                    if other_op is operator.le:
                        if other_version > version:
                            del other_reqs[index]
                        else:
                            keep_req = False
                    # check for other ge, version <= error
                    elif other_op is operator.ge:
                        if other_version > version:
                            raise IncompatibleVersion(name, current, other)
                    # check for eq not in range
                    elif other_op is operator.eq:
                        if other_version > version:
                            raise IncompatibleVersion(name, current, other)
                    # check for neq in range or remove it
                    elif other_op is operator.ne:
                        if other_version > version:
                            del other_reqs[index]

                if op is operator.ne:
                    # check for other ne, version == remove self
                    if other_op is operator.ne:
                        if other_version == version:
                            del other_reqs[index]
                    # check for other eq, version == other, error
                    elif other_op is operator.eq:
                        if other_version == version:
                            raise IncompatibleVersion(name, current, other)
                    # check for le, not in range remove
                    elif other_op is operator.le:
                        if other_version < version:
                            keep_req = False
                    # check for ge, not in range remove
                    elif other_op is operator.ge:
                        if other_version > version:
                            keep_req = False
            return keep_req

        keep_current = reduce_reqs(new_reqs) and keep_current
        keep_current = reduce_reqs(consume_reqs) and keep_current
        if keep_current:
            new_reqs.append((op, version))
    new_reqs.sort(key=operator.itemgetter(1))
    return new_reqs


class Requirement(object):
    """Represent a requirement.
    """

    def __init__(self, name, versions=None, extras=None):
        self.name = name
        self.key = keyify(name)
        self.versions = versions or []
        if extras is None:
            extras = frozenset()
        self.extras = extras

    @classmethod
    def parse(cls, requirement):
        groups = REQUIREMENT_NAME_PARSE.match(requirement).groupdict()
        version_requirements = []
        for op, version in REQUIREMENT_VERSION_PARSE.findall(
            groups['requirements']):
            if version != 'dev':
                # We ignore the dev crap
                version_requirements.append(
                    (REQUIREMENT_TO_OPERATORS(op),
                     Version.parse(version)))
        extras = groups.get('extras', None)
        if extras:
            extras = frozenset(s.strip() for s in extras.split(','))
        return cls(groups['name'], version_requirements, extras)

    def match(self, release):
        """Tells you if the given release match the requirement of
        not.
        """
        if release.key != self.key:
            return False
        for op, version in self.versions:
            if not op(release.version, version):
                return False
        # XXX We should check this
        # for extra in self.extras:
        #     if extra not in release.extras:
        #         return False
        return True

    def is_unique(self):
        """Tells you if only one unique version can match the
        requirement, or if mutliple are possible.
        """
        for op, version in self.versions:
            if op is operator.eq:
                return True
        return False

    def is_compatible(self, other):
        """Tells you if two requirement are compatible together. It
        can return True, a merged requirement or raise an exception if
        they are not compatible.
        """
        assert isinstance(other, Requirement)
        if self.key != other.key:
            return True
        return False

    def __str__(self):
        name = self.name
        if self.extras:
            name += '[' + ','.join(sorted(self.extras)) + ']'
        if self.versions:
            specificators = []
            for operator, version in self.versions:
                specificators.append(
                    OPERATORS_TO_REQUIREMENT(operator) + str(version))
            name += ','.join(specificators)
        return name

    def __add__(self, other):
        if not isinstance(other, Requirement) or self.key != other.key:
            raise InvalidRequirement(other)
        return self.__class__(
            self.name,
            reduce_requirements(self.name, self.versions, other.versions),
            self.extras | other.extras)

    def __repr__(self):
        return '<Requirement %s>' % str(self)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if isinstance(other, Requirement):
            return self.key == other.key and self.versions == other.versions
        return False


class Requirements(object):
    """Represent a list of requirements.
    """

    def __init__(self, *requirements):
        self.__order = [r.key for r in requirements]
        self.__data = dict((r.key, r) for r in requirements)

    @property
    def requirements(self):
        return self.__data.values()

    @classmethod
    def parse(cls, requirements):
        # We can parse a list of requirements
        if not isinstance(requirements, list):
            requirements = [requirements,]

        return cls(*map(Requirement.parse, requirements))

    def append(self, requirement):
        key = requirement.key
        if key in self.__data:
            self.__data[key] += requirement
        else:
            self.__data[key] = requirement
            self.__order.append(key)

    def remove(self, requirement):
        key = requirement.key
        del self.__data[key]
        self.__order.remove(key)

    def pop(self):
        key = self.__order.pop(0)
        requirement = self.__data[key]
        del self.__data[key]
        return requirement

    def get(self, requirement, default=None):
        if isinstance(requirement, Requirement):
            return self.__data.get(requirement.key, default)
        self.__data.get(keyify(requirement), default)

    def __getitem__(self, requirement):
        requirement = self.get(requirement)
        if requirement is None:
            raise KeyError(requirement)
        return requirement

    def __contains__(self, requirement):
        contained = self.__data.get(requirement.key)
        if contained is not None:
            reduce_requirements(
                requirement.name,
                requirement.versions,
                contained.versions)
            return True
        return False

    def __iter__(self):
        return self.__data.itervalues()

    def __len__(self):
        return len(self.__order)

    def __str__(self):
        return '\n'.join(str(r) for r in
                         sorted(self.__data.values(),
                                key=operator.attrgetter('name')))

    def __add__(self, other):
        if not isinstance(other, Requirements):
            raise ValueError(other)
        merged = {}
        for requirement in other.requirements:
            key = requirement.key
            if key in self.__data:
                merged[key] = self.__data[key] + requirement
            else:
                merged[key] = requirement
        for key, requirement in self.__data.iteritems():
            if key not in merged:
                merged[key] = requirement
        return self.__class__(*merged.values())

    def __repr__(self):
        return '<Requirements %s>' % ', '.join(map(str, self.requirements))
