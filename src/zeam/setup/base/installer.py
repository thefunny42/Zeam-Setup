
import logging
import os.path
import threading

from zeam.setup.base.distribution.kgs import get_kgs_requirements
from zeam.setup.base.error import PackageError, logs
from zeam.setup.base.version import Requirements

logger = logging.getLogger('zeam.setup')
INSTALLATION_DONE = object()


class PackageInstaller(object):
    """Package installer: install new package in a working set from
    sources.
    """

    def __init__(self, options, working_set):
        __status__ = u"Configuring package installer."
        self.interpretor = working_set.interpretor
        self.working_set = working_set
        self.kgs = get_kgs_requirements(options)
        self.sources = options.utilities.sources
        self._to_install = Requirements()
        self._verify_being_installed = Requirements()
        self._being_installed = Requirements()
        self._lock = threading.RLock()
        self._wait = threading.Condition(threading.RLock())
        self._worker_count = options.get_with_default(
            'install_workers', 'setup', '5').as_int()
        self._options = options
        self._first_done = False
        self._error = None

    def _wakeup_workers(self):
        # Wake up some workers to work.
        count_to_wake_up = max(
            self._worker_count - 1, len(self._to_install))
        self._wait.acquire()
        for count in range(count_to_wake_up):
            self._wait.notify()
        self._wait.release()

    def _verify_extra_install(self, requirement):
        # Verify is some extra need installation
        release = self.working_set[requirement]
        for extra in requirement.extras:
            if extra not in release.extras:
                raise PackageError(
                    u'Require missing extra requirements "%s" in "%s"' % (
                        extra, release))
            self._register_install(release.extras[extra])

    def _register_install(self, requirements):
        # Mark requirements to be installed.
        for requirement in requirements:
            if self.kgs is not None:
                requirement = self.kgs.upgrade(requirement)
            if requirement in self.working_set:
                if requirement.extras:
                    self._verify_extra_install(requirement)
                logger.debug(
                    u'Skip already installed dependency %s', requirement)
                continue
            if requirement in self._being_installed:
                if requirement.extras:
                    self._verify_being_installed.append(requirement)
                logger.debug(
                    u'Skip already being installed dependency %s',
                    requirement)
                continue
            logger.debug(
                u'Need to install dependency %s', requirement)
            self._to_install.append(requirement)

    def wait_for_requirements(self):
        logger.debug(u'Wait for dependencies')
        self._wait.acquire()
        self._wait.wait()
        self._wait.release()

    def mark_failed(self, error):
        self._lock.acquire()
        try:
            logger.debug(u'Failure')
            self._error = error
            logs.report(fatal=False)
            self._wait.acquire()
            self._wait.notifyAll()
            self._wait.release()
        finally:
            self._lock.release()

    def get_requirement(self):
        self._lock.acquire()
        try:
            if self._error is not None:
                return INSTALLATION_DONE
            if not self._to_install:
                if not self._being_installed:
                    if not self._first_done:
                        # Wake up other waiting worker
                        self._wait.acquire()
                        self._wait.notifyAll()
                        self._wait.release()
                        self._first_done = True
                    return INSTALLATION_DONE
                return None
            requirement = self._to_install.pop()
            assert requirement not in self._being_installed
            self._being_installed.append(requirement)
            logger.info(u'Installing %s', requirement)
            return requirement
        finally:
            self._lock.release()

    def mark_installed(self, requirement, package):
        self._lock.acquire()
        try:
            self.working_set.add(package)
            if requirement in self._verify_being_installed:
                extra_requirement = self._verify_being_installed[requirement]
                logger.debug(
                    u'Verify pending extra for %s', extra_requirement)
                worker_need_wake_up = len(self._to_install) == 0
                self._verify_extra_install(extra_requirement)
                if worker_need_wake_up:
                    self._wakeup_workers()
                self._verify_being_installed.remove(extra_requirement)
            self._being_installed.remove(requirement)
            logger.debug(u'Mark %s as installed', requirement)
        finally:
            self._lock.release()

    def install_dependencies(self, requirements):
        self._lock.acquire()
        try:
            worker_need_wake_up = len(self._to_install) == 0
            self._register_install(requirements)
            if worker_need_wake_up:
                self._wakeup_workers()
        finally:
            self._lock.release()

    def __call__(self, requirements, directory=None):
        __status__ = u"Installing %r." % (requirements)
        if directory is None:
            directory = self._options.get_with_default(
                'lib_directory', 'setup').as_text()
        self._register_install(requirements)
        if self._to_install:
            self.sources.initialize()
            workers = []
            for count in range(self._worker_count):
                worker = PackageInstallerWorker(self, directory, count)
                worker.start()
                workers.append(worker)
            for worker in workers:
                worker.join()
            if self._error is not None:
                raise self._error
            else:
                if self.kgs is not None:
                    self.kgs.log_usage()
        return self.working_set


class PackageInstallerWorker(threading.Thread):
    """'Resolve' packages, i.e. find a package that match a
    requirements and its dependencies.
    """

    def __init__(self, manager, target_directory, count):
        super(PackageInstallerWorker, self).__init__(
            name='installer %d' % count)
        self.manager = manager
        self.interpretor = manager.interpretor
        self.sources = manager.sources
        self.target_directory = os.path.abspath(target_directory)

    def install_dependencies(self, requirement, distribution):
        install = self.manager.install_dependencies
        install(distribution.requirements)
        for extra in requirement.extras:
            if extra not in distribution.extras:
                raise PackageError(
                    u'Require missing extra requirements "%s" in "%s"' % (
                        extra, distribution))
            install(distribution.extras[extra])

    def install(self, requirement):
        """Install the given package name in the directory.
        """
        __status__ = u"Installing %s." % requirement
        candidate_packages = self.sources.search(
            requirement, self.interpretor)
        package = candidate_packages.get_most_recent()
        logger.info(
            u"Choosing version %s for %s.", str(package.version), requirement)
        release, loader = package.install(
            self.target_directory,
            self.interpretor,
            lambda distribution: self.install_dependencies(
                requirement, distribution))
        return release

    def run(self):
        """Install packages as long as you can.
        """
        logs.register(self.getName())
        try:
            while True:
                requirement = self.manager.get_requirement()
                if requirement is None:
                    self.manager.wait_for_requirements()
                    continue
                if requirement is INSTALLATION_DONE:
                    break
                self.manager.mark_installed(
                    requirement, self.install(requirement))
        except Exception, error:
            self.manager.mark_failed(error)
        finally:
            logs.unregister()
