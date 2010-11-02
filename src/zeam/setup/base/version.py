
import re
import operator

VERSION_PARTS = re.compile(r'(\d+|[a-z]+|\.|-)')
VERSION_REPLACE = {
    'pre':'c', 'preview':'c', '-':'final-', 'post': 'final-', 'rc':'c'}.get
REQUIREMENT_NAME_PARSE = re.compile(
    r'^(?P<name>[\w.]+)\s*(\[(?P<extras>[\w\s.,]+)\])?\s*(?P<requirements>.*)$')
REQUIREMENT_VERSION_PARSE = re.compile(
    r'(?P<operator>[<>=!]=)\s*(?P<version>[\da-z.\-]+)\s*,?')
REQUIREMENT_TO_OPERATORS = {'==': operator.eq, '>=': operator.ge,
                            '!=': operator.ne, '<=': operator.le}.get
OPERATORS_TO_REQUIREMENT = {operator.eq: '==', operator.ge: '>=',
                            operator.ne: '!=', operator.le: '<='}.get


class InvalidVersion(ValueError):
    """This version is invalid.
    """

class InvalidRequirement(ValueError):
    """Those requirement are invalids.
    """

class IncompatibleRequirement(InvalidRequirement):
    """Those reauirement are not compatible together.
    """


class Version(object):
    """Represent a version of a software.
    """

    def __init__(self, *version):
        self.version = version

    @classmethod
    def parse(klass, version):
        # This algo comes from setuptools
        def split_version_in_parts():
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
        return klass(*parsed_version)

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
        return '%s.parse(%r)' % (self.__class__.__name__, self.__str__())


def reduce_requirements(*reqs):
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
                            raise IncompatibleRequirement(current, other)
                    elif other_op is operator.ne:
                        # check if != version == error else remove
                        if other_version == version:
                            raise IncompatibleRequirement(current, other)
                        else:
                            del other_reqs[index]
                    elif other_op is operator.le:
                        # check if version is in range
                        if other_version < version:
                            raise IncompatibleRequirement(current, other)
                        else:
                            del other_reqs[index]
                    elif other_op is operator.ge:
                        # check if version is in range
                        if other_version > version:
                            raise IncompatibleRequirement(current, other)
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
                            raise IncompatibleRequirement(current, other)
                    # check for eq not in range
                    elif other_op is operator.eq:
                        if other_version < version:
                            raise IncompatibleRequirement(current, other)
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
                            raise IncompatibleRequirement(current, other)
                    # check for eq not in range
                    elif other_op is operator.eq:
                        if other_version > version:
                            raise IncompatibleRequirement(current, other)
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
                            raise IncompatibleRequirement(current, other)
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

    def __init__(self, name, versions, extras=None):
        self.name = name
        self.versions = versions
        if extras is None:
            extras = frozenset()
        self.extras = extras

    @classmethod
    def parse(cls, requirement):
        groups = REQUIREMENT_NAME_PARSE.match(requirement).groupdict()
        version_requirements = []
        for operator, version in REQUIREMENT_VERSION_PARSE.findall(
            groups['requirements']):
            version_requirements.append(
                (REQUIREMENT_TO_OPERATORS(operator),
                 Version.parse(version)))
        extras = groups.get('extras', None)
        if extras:
            extras = frozenset(s.strip() for s in extras.split(','))
        return cls(groups['name'], version_requirements, extras)

    def match(self, release):
        """Tells you if the given release match the requirement of
        not.
        """
        if release.name != self.name:
            return False
        for op, version in self.versions:
            if not op(release.version, version):
                return False
        return True

    def is_compatible(self, other):
        """Tells you if two requirement are compatible together. It
        can return True, a merged requirement or raise an exception if
        they are not compatible.
        """
        assert isinstance(other, Requirement)
        if self.name != other.name:
            return True

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
        if not isinstance(other, Requirement) or self.name != other.name:
            raise InvalidRequirement(other)
        return self.__class__(
            self.name,
            reduce_requirements(self.versions, other.versions),
            self.extras | other.extras)

    def __repr__(self):
        return '<Requirement %s>' % str(self)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if isinstance(other, Requirement):
            return self.name == other.name and self.versions == other.versions
        return False


class Requirements(object):
    """Represent a list of requirements.
    """

    def __init__(self, *requirements):
        self.__order = [r.name for r in requirements]
        self.__data = dict((r.name, r) for r in requirements)

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
        name = requirement.name
        if name in self.__data:
            self.__data[name] += requirement
        else:
            self.__data[name] = requirement
            self.__order.append(name)

    def remove(self, requirement):
        name = requirement.name
        del self.__data[name]
        self.__order.remove(name)

    def pop(self):
        name = self.__order.pop(0)
        requirement = self.__data[name]
        del self.__data[name]
        return requirement

    def __contains__(self, requirement):
        contained = self.__data.get(requirement.name)
        if contained is not None:
            reduce_requirements(requirement.versions, contained.versions)
            return True
        return False

    def __iter__(self):
        return self.__data.itervalues()

    def __len__(self):
        return len(self.__order)

    def __str__(self):
        return '\n'.join(str(r) for name, r in
                         sorted(self.__data.items(),
                                key=operator.itemgetter(0)))

    def __add__(self, other):
        if not isinstance(other, Requirements):
            raise ValueError(other)
        merged = {}
        for requirement in other.requirements:
            name = requirement.name
            if name in self.__data:
                merged[name] = self.__data[name] + requirement
            else:
                merged[name] = requirement
        for name, requirement in self.__data.iteritems():
            if name not in merged:
                merged[name] = requirement
        return self.__class__(*merged.values())

    def __repr__(self):
        return '<Requirements %s>' % ', '.join(map(str, self.requirements))
