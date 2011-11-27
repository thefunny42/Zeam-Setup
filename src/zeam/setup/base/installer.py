
import logging
import os.path
import threading

from zeam.setup.base.distribution.kgs import get_kgs_requirements
from zeam.setup.base.error import PackageError, report_error
from zeam.setup.base.version import Requirements
from zeam.setup.base.utils import get_option_with_default

logger = logging.getLogger('zeam.setup')
INSTALLATION_DONE = object()


class PackageInstaller(object):
    """Package installer: install new package in a working set from
    sources.
    """

    def __init__(self, options, working_set, no_kgs=False):
        __status__ = u"Configuring package installer."
        configuration = options.configuration
        self.interpretor = working_set.interpretor
        self.working_set = working_set
        self.sources = configuration.utilities.sources
        self.__to_install = Requirements()
        self.__being_installed = Requirements()
        self.__installed = Requirements()
        self.__lock = threading.RLock()
        self.__wait = threading.Condition(threading.RLock())
        self.kgs = None
        setup = configuration['setup']
        versions = get_option_with_default('versions', options, False)
        if versions is not None:
            self.kgs = get_kgs_requirements(versions.as_list(), configuration)
        self.__worker_count = setup.get('workers', '4').as_int()
        self.__lib_directory = setup.get('lib_directory').as_text()
        self.__first_done = False
        self.__installation_failed = None

    def __register_install(self, requirement):
        if self.kgs is not None:
            requirement = self.kgs.upgrade(requirement)
        if (requirement in self.working_set or
            requirement in self.__installed or
            requirement in self.__being_installed):
            return
        self.__to_install.append(requirement)

    def wait_for_requirements(self):
        self.__wait.acquire()
        self.__wait.wait()
        self.__wait.release()

    def mark_failed(self, error):
        self.__lock.acquire()
        self.__installation_failed = error
        self.__wait.acquire()
        self.__wait.notify_all()
        self.__wait.release()
        self.__lock.release()

    def get_requirement(self):
        self.__lock.acquire()
        try:
            if self.__installation_failed is not None:
                return INSTALLATION_DONE
            if not self.__to_install:
                if not self.__being_installed:
                    if not self.__first_done:
                        # Wake up other waiting worker
                        self.__wait.acquire()
                        self.__wait.notify_all()
                        self.__wait.release()
                        self.__first_done = True
                    return INSTALLATION_DONE
                return None
            requirement = self.__to_install.pop()
            assert requirement not in self.__being_installed
            self.__being_installed.append(requirement)
            return requirement
        finally:
            self.__lock.release()

    def mark_installed(self, requirement, package):
        self.__lock.acquire()
        self.__being_installed.remove(requirement)
        self.__installed.append(requirement)
        self.working_set.add(package)
        self.__lock.release()

    def install_dependencies(self, requirements):
        self.__lock.acquire()
        worker_need_wake_up = len(self.__to_install) == 0
        for requirement in requirements:
            self.__register_install(requirement)
        if worker_need_wake_up:
            count_to_wake_up = max(
                self.__worker_count - 1, len(self.__to_install))
            self.__wait.acquire()
            for count in range(count_to_wake_up):
                self.__wait.notify()
            self.__wait.release()
        self.__lock.release()

    def __call__(self, requirements, target_directory=None):
        __status__ = u"Installing %r." % (requirements)
        if target_directory is None:
            target_directory = self.__lib_directory
        for requirement in requirements:
            self.__register_install(requirement)
        if self.__to_install:
            self.sources.initialize()
            workers = []
            for count in range(self.__worker_count):
                worker = PackageInstallerWorker(self, target_directory)
                worker.start()
                workers.append(worker)
            for worker in workers:
                worker.join()
            if self.__installation_failed is not None:
                raise self.__installation_failed
            else:
                if self.kgs is not None:
                    self.kgs.log_usage()


class PackageInstallerWorker(threading.Thread):
    """'Resolve' packages, i.e. find a package that match a
    requirements and its dependencies.
    """

    def __init__(self, manager, target_directory):
        super(PackageInstallerWorker, self).__init__()
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
                    u'Require missing extra %s in %s' % (extra, distribution))
            install(distribution.extras[extra])

    def install(self, requirement):
        """Install the given package name in the directory.
        """
        __status__ = u"Installing %s." % requirement
        candidate_packages = self.sources.search(
            requirement, self.interpretor)
        package = candidate_packages.get_most_recent()
        logger.info(u"Humbly choosing version %s for %s." % (
                str(package.version), requirement))
        release, loader = package.install(
            self.target_directory,
            self.interpretor,
            lambda distribution: self.install_dependencies(
                requirement, distribution))
        return release

    def run(self):
        """Install packages as long as you can.
        """
        try:
            while True:
                requirement = self.manager.get_requirement()
                if requirement is None:
                    self.manager.wait_for_requirements()
                    continue
                if requirement is INSTALLATION_DONE:
                    break
                package = self.install(requirement)
                self.manager.mark_installed(requirement, package)
        except Exception, error:
            report_error(debug=True, fatal=False)
            self.manager.mark_failed(error)


