import os
import shelve
import logging
import pickle
from twisted.internet import defer


class QueryCache(object):
    def __init__(self, cache_dir):
        self._cache_dir = cache_dir
        self._logger = logging.getLogger(__name__)

    @staticmethod
    def _fullname(o):
        return o.__module__ + "." + o.__class__.__name__

    def cache(self, f):
        full_name = self._fullname(f)
        cache_db = shelve.open(os.path.join(self._cache_dir, full_name))

        @defer.deferredGenerator
        def wrapper(*args, **kwargs):
            all_args = pickle.dumps((args, kwargs))
            if all_args in cache_db:
                result = cache_db[all_args]
                self._logger.debug('%s(%s) - Cache hit (%r)', full_name, ((args, kwargs)), result)
            else:
                d = defer.waitForDeferred(defer.maybeDeferred(f, *args, **kwargs))
                yield d
                result = d.getResult()
                self._logger.debug('%s(%s) - Cache miss (%r)', full_name, ((args, kwargs)), result)
                cache_db[all_args] = result
                cache_db.sync()

            yield result

        return wrapper
