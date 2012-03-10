
import threading

marker = object()


class CallbackUtility(object):
    """Simple utility registering callbacks.
    """

    def __init__(self, configuration):
        self._callbacks = []
        self._executed = False

    def register(self, callback):
        if self._executed:
            callback()
        else:
            self._callbacks.append(callback)

    def execute(self):
        if not self._executed:
            for callback in self._callbacks:
                callback()
        self._executed = True


class Utilities(object):
    """Utility registry.
    """

    def __init__(self, configuration):
        self._configuration = configuration
        self._lock = threading.Lock()
        self._utilities = {}
        self._factories = {}
        self.register('atexit', CallbackUtility)

    def register(self, name, factory):
        self._factories[name] = factory

    def reset(self):
        self._lock.acquire()
        try:
            del self._utilities[:]
        except:
            self._lock.release()

    def get(self, key, default=None):
        if key in self._utilities:
            return self._utilities[key]
        if key in self._factories:
            self._lock.acquire()
            try:
                # We migth have one instance now, try again.
                if key in self._utilities:
                    return self._utilities[key]
                utility = self._factories[key](self._configuration)
                self._utilities[key] = utility
                return utility
            finally:
                self._lock.release()
        if default is marker:
            raise AttributeError(key)
        return default

    def __getattr__(self, key):
        return self.get(key, marker)
