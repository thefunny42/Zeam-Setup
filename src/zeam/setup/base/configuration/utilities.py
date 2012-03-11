
import threading

marker = object()

class Utilities(object):
    """Utility registry.
    """

    def __init__(self, configuration):
        self._configuration = configuration
        self._lock = threading.Lock()
        self._utilities = {}
        self._factories = {}

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
