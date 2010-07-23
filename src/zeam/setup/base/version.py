
import re
import operator

VERSION_PARTS = re.compile(r'(\d+|[a-z]+|\.|-)')
VERSION_REPLACE = {'pre':'c', 'preview':'c', '-':'final-', 'rc':'c',}.get
REQUIREMENT_NAME_PARSE = re.compile(
    r'^(?P<name>[\w.]+)\s*(?P<requirements>.*)$')
REQUIREMENT_VERSION_PARSE = re.compile(
    r'(?P<operator>[<>=!]=)\s*(?P<version>[\da-z.\-]+)\s*,?')
REQUIREMENT_TO_OPERATORS = {'==': operator.eq, '>=': operator.ge,
                            '!=': operator.ne, '<=': operator.le}.get
OPERATORS_TO_REQUIREMENT = {operator.eq: '==', operator.ge: '>=',
                            operator.ne: '!=', operator.le: '<='}.get


class InvalidRequirement(ValueError):
    """Those requirement are invalids.
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
                else:
                    yield '*' + part
            yield '*final'

        parsed_version = []
        for part in split_version_in_parts():
            if part.startswith('*'):
                if part < '*final':   # remove '-' before a prerelease tag
                    while parsed_version and parsed_version[-1] == '*final-':
                        parsed_version.pop()
                # remove trailing zeros from each series of numeric parts
                while parsed_version and parsed_version[-1] == '00000000':
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
                rendered_version.append(part[1:])
            elif need_dot:
                rendered_version.append('.')
            need_dot = False
            if part[0] == '0':
                rendered_version.append(part.lstrip('0') or '0')
                need_dot = True
        return ''.join(rendered_version)


class IncompatibleRequirement(Exception):
    pass


def reduce_requirements(reqs):
    """Reduce a list of version requirements to a shorter one if possible.
    """
    new_reqs = []
    to_process = list(reqs)
    while len(to_process):
        current = to_process.pop()
        op, version = current
        if op is operators.eq:
            for index, other in enumerate(to_process):
                other_op, other_version = other
                if other_op is operators.eq:
                    # check for other eq, version == remove self, else error
                    if other_version == version:
                        del to_process[index]
                    else:
                        raise IncompatibleRequirement(current, other)
                elif other_op is operators.ne:
                    # check if != version == error else remove
                    if other_version == version:
                        raise IncompatibleRequirement(current, other)
                    else:
                        del to_process[index]
        if op is operators.ge:
            # check for other ge, version >= remove it else remove self
            # check for other le, version <= error
            pass
        if op is operators.le:
            # check for other le, version <= remove it else remove self
            # check for other ge, version >= error
            pass
        if os is operators.ne:
            for index, other in enumerate(to_process):
                other_op, other_version = other
                if other_op is operators.ne:
                    # check for other ne, version == remove self
                    if other_version == version:
                        del to_process[index]

    return new_reqs


class Requirement(object):
    """Represent a requirement.
    """

    def __init__(self, name, versions):
        self.name = name
        self.versions = versions

    @classmethod
    def parse(cls, requirement):
        groups = REQUIREMENT_NAME_PARSE.match(requirement)
        version_requirements = []
        for operator, version in REQUIREMENT_VERSION_PARSE.findall(
            groups.group('requirements')):
            version_requirements.append(
                (REQUIREMENT_TO_OPERATORS(operator),
                 Version.parse(version)))

        return cls(groups.group('name'), version_requirements)

    def match(self, release):
        if release.name != self.name:
            return False
        for op, version in self.versions:
            if not op(release.version, version):
                return False
        return True

    def __str__(self):
        if not self.versions:
            return self.name
        specificators = []
        for operator, version in self.versions:
            specificators.append(
                OPERATORS_TO_REQUIREMENT(operator) + str(version))
        return ''.join((self.name, ','.join(specificators)))

    def __add__(self, other):
        if not isinstance(other, Requirement) or self.name != other.name:
            raise InvalidRequirement(other)
        version_requirements = list(self.versions)
        version_requirements.extend(other.versions)
        return self.__class__(self.name, version_requirements)

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
        self.requirements = requirements

    @classmethod
    def parse(cls, requirements):
        parsed_requirements = []
        # We can parse a list of requirements
        if not isinstance(requirements, list):
            requirements = [requirements,]

        # Parse requirements
        for requirement in requirements:
            parsed_requirements.append(
                Requirement.parse(requirement))

        return cls(*parsed_requirements)

    def __iter__(self):
        return iter(self.requirements)

    def __len__(self):
        return len(self.requirements)

    def __str__(self):
        return '\n'.join(map(str, self.requirements))

    def __repr__(self):
        return '<Requirements %s>' % ', '.join(map(str, self.requirements))
