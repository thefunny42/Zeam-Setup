
import logging
import operator
import os
import threading

from zeam.setup.base.error import logs

logger = logging.getLogger('zeam.setup')
_marker = object()


class Paths(object):

    def __init__(self, paths=None, verify=True):
        self._data = {}
        self._len = 0
        self._verify = verify
        if paths:
            self.extend(paths)

    def add(self, path, verify=None, directory=None, **extra):
        if verify is None:
            verify = self._verify
        if verify:
            if not os.path.exists(path):
                logger.error(
                    u"WARNING: Missing installed path %s.",
                    path)
                return False
        data = self._data
        for piece in path.split(os.path.sep):
            data = data.setdefault(piece, {})
        if directory is None:
            directory = os.path.isdir(path)
        info = {'directory': directory, 'original': path}
        info.update(extra)
        data[None] = info
        self._len += 1
        return True

    def listdir(self, path):
        """Populate the path object from the filesystem.
        """

        def populate(path, prefix):
            for item in os.listdir(path):
                item_prefix = os.path.join(prefix, item)
                item_path = os.path.join(path, item)
                item_directory = os.path.isdir(item_path)
                self.add(item_prefix, verify=False, directory=item_directory)
                if item_directory:
                    populate(item_prefix, item_path)

        populate(path, '')

    def extend(self, paths, verify=None):
        added = True
        for path in paths:
            added = self.add(path, verify=verify) and added
        return added

    def rename(self, old, new):

        def rename_sub(old_data, old_ids, new_data, new_ids):
            assert len(old_ids) == len(new_ids), \
                'Path of different depths are not supported'

            if not old_ids:
                if None not in old_data:
                    raise ValueError
                new_data[None] = old_data[None]
                del old_data[None]
                return len(old_data) == 0

            old_id = old_ids.pop(0)
            new_id = new_ids.pop(0)

            if old_id not in old_data:
                raise ValueError

            add_data = new_data.get(new_id, {})
            unique = len(old_data[old_id]) == 1

            prune = rename_sub(
                old_data[old_id], old_ids,
                add_data, new_ids)

            prune = unique and prune
            new_data[new_id] = add_data

            if old_id == new_id:
                return prune
            if prune:
                del old_data[old_id]
            return prune

        try:
            rename_sub(
                self._data, old.split(os.path.sep),
                self._data, new.split(os.path.sep))
            return True
        except ValueError:
            return False

    def query(self, **matches):
        return self._search(
            lambda key, value: os.path.sep.join(key),
            True, matches=matches)

    def as_list(self, simplify=False, matches={}, prefixes={}):
        return self._search(
            lambda key, value: os.path.sep.join(key),
            simplify=simplify, matches=matches, prefixes=prefixes)

    def as_dict(self, simplify=False, matches={}, prefixes={}):
        return dict(self._search(
            lambda key, value: (os.path.sep.join(key), value),
            simplify=simplify, matches=matches, prefixes=prefixes))

    def _search(self, visitor, simplify=False, matches={}, prefixes={}):
        result = []

        def build(prefix, data):
            for key, value in sorted(data.items(), key=operator.itemgetter(0)):
                if key is None:
                    for match_key, match_value in matches.items():
                        if value.get(match_key, None) != match_value:
                            break
                    else:
                        result.append(visitor(prefix, value))
                        if simplify:
                            # None is always the smallest.
                            break
                else:
                    build(prefix + [key], value)

        if prefixes:
            for path, replace in prefixes.iteritems():
                data = self._data
                for piece in path.split(os.path.sep):
                    data = data.get(piece)
                    if data is None:
                        break
                else:
                    if replace:
                        build([replace], data)
                    else:
                        build([], data)
        else:
            build([], self._data)
        return result

    def get(self, path, default=None):
        data = self._data
        for piece in path.split(os.path.sep):
            data = data.get(piece, _marker)
            if data is _marker:
                return default
        if None in data:
            return data[None]
        return default

    def __len__(self):
        return self._len

    def __getitem__(self, path):
        value = self.get(path, default=_marker)
        if value is _marker:
            raise KeyError(path)
        return value

    def __contains__(self, path):
        return self.get(path, default=_marker) is not _marker


WORK_DONE = object()


class MultiTask(object):

    def __init__(self, options, name):
        self.name = name
        self._lock = threading.RLock()
        self._to_process = []
        self._results = []
        self._error = None
        self._options = options
        self._worker_count = options.get_with_default(
            'install_workers', 'setup', '5').as_int()

    def mark_failed(self, error):
        self._lock.acquire()
        try:
            logger.debug(u'Failure')
            self._error = error
            logs.report(fatal=False)
        finally:
            self._lock.release()

    def mark_done(self, result):
        self._lock.acquire()
        try:
            self._results.append(result)
        finally:
            self._lock.release()

    def get_work(self):
        self._lock.acquire()
        try:
            if self._error is not None:
                return WORK_DONE
            if not self._to_process:
                return WORK_DONE
            return self._to_process.pop()
        finally:
            self._lock.release()

    def __call__(self, processor, items):
        self._to_process = list(items)
        self._results = []

        if self._to_process:
            workers = []
            for count in range(min(len(items), self._worker_count)):
                worker = MultiTaskWorker(self, processor, count)
                worker.start()
                workers.append(worker)
            for worker in workers:
                worker.join()
            if self._error is not None:
                raise self._error
        return self._results


class MultiTaskWorker(threading.Thread):
    """Work.
    """

    def __init__(self, manager, processor, count):
        super(MultiTaskWorker, self).__init__(
            name=''.join((manager.name, ' ', str(count))))
        self.manager = manager
        self.process = processor

    def run(self):
        """Install packages as long as you can.
        """
        logs.register(self.getName())
        try:
            while True:
                task = self.manager.get_work()
                if task is WORK_DONE:
                    break
                self.manager.mark_done(self.process(task))
        except Exception, error:
            self.manager.mark_failed(error)
        finally:
            logs.unregister()
