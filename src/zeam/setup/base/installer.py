
import logging
import os.path
import threading

from zeam.setup.base.error import report_error
from zeam.setup.base.version import Requirements

logger = logging.getLogger('zeam.setup')
INSTALLATION_DONE = object()


class PackageInstaller(object):
    """Package installer: install new package in a working set from
    sources.
    """

    def __init__(self, options, working_set):
        __status__ = u"Configuration package installer."
        configuration = options.configuration
        self.interpretor = working_set.interpretor
        self.working_set = working_set
        self.sources = configuration.utilities.sources
        self.__to_install = Requirements()
        self.__being_installed = Requirements()
        self.__check_install = Requirements()
        self.__installed = Requirements()
        self.__lock = threading.RLock()
        self.__wait = threading.Condition(threading.RLock())
        setup = configuration['setup']
        self.__worker_count = setup.get('workers', '4').as_int()
        self.__lib_directory = setup.get('lib_directory').as_text()

    def wait_for_requirements(self):
        self.__wait.acquire()
        self.__wait.wait()
        self.__wait.release()

    def get_requirement(self):
        self.__lock.acquire()
        try:
            if not self.__to_install:
                if not self.__being_installed:
                    # Wake up other waiting worker
                    self.__wait.acquire()
                    self.__wait.notify_all()
                    self.__wait.release()
                    return INSTALLATION_DONE
                return None
            requirement = self.__to_install.pop()
            assert requirement not in self.__being_installed
            self.__being_installed.append(requirement)
            return requirement
        finally:
            self.__lock.release()

    def set_installed(self, requirement, package):
        self.__lock.acquire()
        self.__being_installed.remove(requirement)
        #if requirement in self.__check_install:
        #    to_check = self.__check_install[requirement]
        #    if (to_check.name == requirement.name and
        #        not to_check.is_compatible(requirement)):
        #        # XXX Conflict no clear
        #        #import pdb ; pdb.set_trace()
        #        pass
        self.__installed.append(requirement)
        self.working_set.add(package)
        self.__lock.release()

    def install_dependencies(self, requirements):
        self.__lock.acquire()
        worker_need_wake_up = len(self.__to_install) == 0
        for requirement in requirements:
            if requirement in self.__installed:
                continue
            if requirement in self.__being_installed:
                self.__check_install.append(requirement)
                continue
            self.__to_install.append(requirement)
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
        self.__to_install += requirements
        self.sources.initialize()
        workers = []
        for count in range(self.__worker_count):
            worker = PackageInstallerWorker(self, target_directory)
            worker.start()
            workers.append(worker)
        for worker in workers:
            worker.join()


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
        self.succeed = True

    def install_dependencies(self, requirements):
        self.manager.install_dependencies(requirements)

    def install(self, requirement):
        """Install the given package name in the directory.
        """
        __status__ = u"Installing %s." % requirement
        candidate_packages = self.sources.search(
            requirement, self.interpretor)
        package = candidate_packages.get_most_recent()
        logger.info(u"Picking version %s for %s." % (
                str(package.version), requirement.name))
        return package.install(
            self.target_directory,
            self.interpretor,
            self.install_dependencies)

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
                self.manager.set_installed(requirement, package)
        except Exception:
            report_error(debug=True, fatal=False)
            self.succeed = False


