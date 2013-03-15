import os
import shelve
import logging
import pickle
import datetime
from twisted.internet import defer


class QueryCache(object):
    def __init__(self, cache_dir):
        self._cache_dir = cache_dir
        self._logger = logging.getLogger(__name__)

    @staticmethod
    def _fullname(o):
        return o.__module__ + "." + o.__class__.__name__

    def cache(self, f, validity):
        full_name = self._fullname(f)
        cache_db = shelve.open(os.path.join(self._cache_dir, full_name))

        @defer.deferredGenerator
        def _record(all_args, *args, **kwargs):
            d = defer.waitForDeferred(defer.maybeDeferred(f, *args, **kwargs))
            yield d
            result = d.getResult()
            self._logger.debug('%s(%s) - Cache miss (%r)', full_name, ((args, kwargs)), result)
            cache_db[all_args] = (result, datetime.datetime.now())
            cache_db.sync()
            yield result

        @defer.deferredGenerator
        def wrapper(*args, **kwargs):
            all_args = pickle.dumps((args, kwargs))
            if all_args in cache_db:
                result, recorded = cache_db[all_args]
                now = datetime.datetime.now()
                if now - recorded > validity:
                    self._logger.debug('%s(%s) - Cache hit (%r), but not valid anymore',
                                       full_name, ((args, kwargs)), result)
                    d = defer.waitForDeferred(_record(all_args, *args, **kwargs))
                    yield d
                    yield d.getResult()
                    return

                self._logger.debug('%s(%s) - Cache hit (%r)', full_name, ((args, kwargs)), result)
                yield result
                return

            d = defer.waitForDeferred(_record(all_args, *args, **kwargs))
            yield d
            yield d.getResult()

        return wrapper
