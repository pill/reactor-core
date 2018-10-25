from __future__ import absolute_import

from abc import ABCMeta, abstractmethod
from redis.exceptions import RedisError
from time import time
import collections
import pickle
import logging
import re

from tornado import gen
from tornado import concurrent

from reactorcore.dao.redis import RedisSource
from reactorcore.services.base import BaseService

logger = logging.getLogger(__name__)

class AbstractCache():
    __metaclass__ = ABCMeta

    @abstractmethod
    def set(self, *args, **kwargs):
        pass

    @abstractmethod
    def unique_add(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_unique_set(self, *args, **kwargs):
        pass

    @abstractmethod
    def get(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_int(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_array(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_multi(self, *keys):
        pass

    @gen.coroutine
    def incr(self, key, ticks=1):
        logger.debug('Incrementing  "%s" by %s', key, ticks)
        return

    @gen.coroutine
    def decr(self, key, ticks=1):
        logger.debug('Decrementing  "%s" by %s', key, ticks)
        yield self.incr(key, ticks * -1)

    @abstractmethod
    def prepend(self, *args, **kwargs):
        pass

    @abstractmethod
    def append(self, *args, **kwargs):
        pass

    @abstractmethod
    def remove(self, *args, **kwargs):
        pass

    @abstractmethod
    def flush(self, *args, **kwargs):
        pass

    @abstractmethod
    def flush_all(self):
        pass

class VoidCache(BaseService, AbstractCache):
    """
    Pass-through cache
    """

    @gen.coroutine
    def set(self, *args, **kwargs):
        return

    @gen.coroutine
    def unique_add(self, *args, **kwargs):
        return

    @gen.coroutine
    def get_unique_set(self, *args, **kwargs):
        pass

    @gen.coroutine
    def get(self, *args, **kwargs):
        return

    @gen.coroutine
    def get_int(self, *args, **kwargs):
        return 0

    @gen.coroutine
    def get_array(self, *args, **kwargs):
        return []

    @gen.coroutine
    def incr(self, key, ticks=1):
        pass

    @gen.coroutine
    def decr(self, key, ticks=1):
        pass

    @gen.coroutine
    def delete(self, *args, **kwargs):
        pass

    @gen.coroutine
    def flush(self, *args, **kwargs):
        pass

    @gen.coroutine
    def flush_all(self):
        pass

    @gen.coroutine
    def get_multi(self, *keys_in):
        raise gen.Return(dict.fromkeys(keys_in))


class RedisCache(RedisSource, BaseService, AbstractCache):
    """
    Redis-based cache
    """

    FLUSH_STEP = 1000

    def __init__(self):
        super(RedisCache, self).__init__(name='CACHE', cls=self.__class__)
        self.prefix = 'cache:'

    @concurrent.run_on_executor
    def set(self, key, value, expire=None):
        logger.debug('Setting cache key "%s" with TTL %s', key, expire)

        key = self.prefix + key
        pickled_val = pickle.dumps(value)

        try:
            if expire is not None:
                # Add key and define an expire in a pipeline for atomicity
                with self.client.pipeline() as pipe:
                    pipe.set(key, pickled_val)
                    pipe.expire(key, expire)
                    pipe.execute()
            else:
                self.client.set(key, pickled_val)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache SET: %s', ex.message, exc_info=True)

    @concurrent.run_on_executor
    def get(self, key):
        logger.debug('Getting  key "%s"', key)

        key = self.prefix + key
        data = None

        value = None

        try:
            data = self.client.get(key)
            # unpickle
            value = pickle.loads(data) if data else None

            logger.debug('Value for "%s": %s', key, value)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache GET: %s', ex.message, exc_info=True)

        return value

    @gen.coroutine
    def unique_add(self, set_name, value):
        logger.debug('Adding "%s" to set "%s"', value, set_name)

        try:
            self.client.sadd(set_name, value)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache GET: %s', ex.message, exc_info=True)

    @gen.coroutine
    def get_unique_set(self, set_name):
        logger.debug('Getting set "%s"', set_name)
        try:
            members = self.client.smembers(set_name)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache GET: %s', ex.message, exc_info=True)

        members = members or set()
        logger.debug('%s items in "%s"', len(members), set_name)
        return members

    @concurrent.run_on_executor
    def get_int(self, key):
        logger.debug('Getting  key "%s"', key)

        key = self.prefix + key
        value = None

        try:
            value = self.client.get(key)
            logger.debug('Value for "%s": %s', key, value)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache GET: %s', ex.message, exc_info=True)

        return value or 0

    @concurrent.run_on_executor
    def get_array(self, key, count=None):
        assert count
        logger.debug('Getting array for key "%s" with %s items', key, count)

        key = self.prefix + key
        arr = []
        try:
            data = self.client.lrange(key, 0, count - 1)

            # unpickle elements
            if data:
                arr = map(lambda x: pickle.loads(x), data)

            logger.debug('Value for "%s": %s', key, arr)

        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache GET: %s', ex.message, exc_info=True)

        return arr

    @concurrent.run_on_executor
    def get_multi(self, *keys_in):
        if not keys_in:
            return None

        logger.debug('Getting keys "%s"', keys_in)
        keys = [self.prefix + key for key in keys_in]

        lookup = None

        try:
            data = self.client.mget(keys)

            # unpickle values
            values = [(val and pickle.loads(str(val))) or None for val in data]

            # remove the cache prefix from keys
            keys = [key[len(self.prefix):] for key in keys]

            # pack into key/val dictionary so it's more usable for the client
            lookup = dict(zip(keys, values))

            logger.debug('Cache data: %s', lookup)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache MGET: %s', ex.message, exc_info=True)
            return dict.fromkeys(keys_in)
        except pickle.UnpicklingError as ex:
            logger.critical('[EXCEPTION] Unpickle error: %s', ex.message, exc_info=True)
            return dict.fromkeys(keys_in)

        return lookup

    @concurrent.run_on_executor
    def incr(self, key, ticks=1):
        assert key
        logger.debug('Incrementing "%s" by %s', key, ticks)
        key = self.prefix + key
        try:
            self.client.incr(key, ticks)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache INCR: %s', ex.message, exc_info=True)

    @gen.coroutine
    def prepend(self, key, value, size=1000):
        assert key
        assert size > 1
        logger.debug('Prepending "%s" to %s', value, key)
        key = self.prefix + key
        pickled_val = pickle.dumps(value)

        try:
            with self.client.pipeline() as pipe:
                pipe.lpush(key, pickled_val)
                pipe.ltrim(key, 0, size - 1)
                pipe.execute()
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache PREPEND: %s', ex.message, exc_info=True)

    @gen.coroutine
    def append(self, key, value, size=1000):
        assert key
        assert size > 1
        logger.debug('Appending "%s" to %s', value, key)
        key = self.prefix + key
        pickled_val = pickle.dumps(value)

        try:
            with self.client.pipeline() as pipe:
                pipe.rpush(key, pickled_val)
                pipe.ltrim(key, 0, size - 1)
                pipe.execute()
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache APPEND: %s', ex.message, exc_info=True)

    @concurrent.run_on_executor
    def remove(self, *keys_in):
        if not keys_in:
            return None

        logger.debug('Deleting keys %s', keys_in)

        # add prefix
        keys = [self.prefix + key for key in keys_in]

        try:
            with self.client.pipeline() as pipe:
                pipe.delete(*keys)
                pipe.execute()
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache DELETE: %s', ex.message, exc_info=True)


    @concurrent.run_on_executor
    def flush(self, pattern=None):
        if not pattern:
            return
        logger.debug('Flushing pattern "%s"', pattern)

        try:
            """Flush all cache (by group of step keys for efficiency),
            or only keys matching an optional pattern"""
            keys = self.client.keys(self.prefix + pattern)
            for i in xrange(0, len(keys), self.FLUSH_STEP):
                keys_to_flush = keys[i:i + self.FLUSH_STEP]
                logger.debug('Flushing cache keys %s', keys_to_flush)
                self.client.delete(*keys_to_flush)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache FLUSH: %s', ex.message, exc_info=True)

    @concurrent.run_on_executor
    def flush_all(self):
        logger.debug('FLUSH ALL')
        # flush all keys for this environment
        return self.flush(self.prefix + '*')

    """
    Add hashing functionality
    """

    @gen.coroutine
    def set_hash(self, key, val):
        key = self.prefix + key
        try:
            self.client.hmset(key, val)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache HASH SET: %s', ex.message, exc_info=True)

    @gen.coroutine
    def delete_hash_key(self, r_hash, *keys):
        r_hash = self.prefix + r_hash
        try:
            return self.client.hdel(r_hash, *keys)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache HASH DEL: %s', ex.message, exc_info=True)

    @gen.coroutine
    def get_hash(self, key, hash_key):
        key = self.prefix + key
        try:
            return self.client.hget(key, hash_key)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache HASH GET: %s', ex.message, exc_info=True)

    @gen.coroutine
    def get_all_hashes(self, key):
        key = self.prefix + key
        try:
            return self.client.hgetall(key)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache GET ALL HASHES: %s', ex.message, exec_info=True)

    @gen.coroutine
    def get_hash_size(self, key):
        key = self.prefix + key
        try:
            return self.client.hlen(key)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache GET HASH LENGTH: %s', ex.message, exec_info=True)


    @gen.coroutine
    def get_keys(self, pattern):
        try:
            return self.client.keys(pattern)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache GET KEYS: %s', ex.message, exec_info=True)

    @gen.coroutine
    def trim_array(self, key, start, end):
        key = self.prefix + key
        try:
            return self.client.ltrim(key, start, end)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache TRIM ARRAY: %s', ex.message, exec_info=True)

    @gen.coroutine
    def set_zset(self, key, **sets):
        key = self.prefix + key
        try:
            return self.client.zadd(key, **sets)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache SET ZSET: %s', ex.message, exec_info=True)

    @gen.coroutine
    def get_zrangebyscore(self, key, min_score, max_score, start=None, num=None, withscores=False):
        key = self.prefix + key
        try:
            return self.client.zrangebyscore(key, min_score, max_score, start=start, num=num,
                withscores=withscores)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache GET ZRANGEBYSCORE: %s', ex.message, exec_info=True)

    @gen.coroutine
    def del_zrangebyscore(self, key, min_score, max_score):
        key = self.prefix + key
        try:
            return self.client.zremrangebyscore(key, min_score, max_score)
        except RedisError as ex:
            logger.critical('[EXCEPTION] Error on cache ZREMRANGEBYSCORE: %s', ex.message, exec_info=True)


class MemoryCache(AbstractCache):
    """
    A very simple implementation of memory-based caching,
    to test the interface and decorators.
    """

    def __init__(self):
        self._cache = dict()
        self.hits = 0
        self.misses = 0

    @gen.coroutine
    def set(self, key, value, expire=None):
        logger.debug('Setting cache key "%s" with TTL %s', key, expire)

        self._cache[key] = {
            'ttl': expire,
            'created': time(),
            'val': value
        }

    @gen.coroutine
    def unique_add(self, set_name, value):
        logger.debug('Adding "%s" to set "%s"', value, set_name)

        if set_name not in self._cache:
            self._cache[set_name] = set()

        self._cache[set_name].add(value)

    @gen.coroutine
    def get_unique_set(self, set_name):
        assert set_name
        members = self._cache.get(set_name, set())
        raise gen.Return(members)

    @gen.coroutine
    def get(self, key):
        if key not in self._cache:
            self.misses += 1
            logger.debug('Cache miss for "%s"', key)
            raise gen.Return(None)

        value = self._cache.get(key)

        # expire if needed
        ttl = value['ttl']
        logger.debug('TTL for "%s": %s', key, ttl)

        key_life = int(time() - value['created'])
        logger.debug('Key life for "%s": %s', key, key_life)

        if ttl is not None and key_life >= ttl:
            logger.debug('Expiring "%s"', key)
            logger.debug('Cache miss for "%s"', key)
            self.misses += 1
            self._cache.pop(key)
            raise gen.Return(None)

        logger.debug('Cache hit for "%s": %s', key, value['val'])
        self.hits += 1
        raise gen.Return(value['val'])

    @gen.coroutine
    def get_int(self, key):
        val = yield self.get(key)
        raise gen.Return(val or 0)

    @gen.coroutine
    def get_array(self, key, count=None):
        assert count
        arr = yield self.get(key)
        arr = arr or []
        raise gen.Return(arr[:count])

    @gen.coroutine
    def get_multi(self, *keys):
        logger.debug('Getting keys "%s"', keys)

        values = yield [self.get(key) for key in keys]

        lookup = dict(zip(keys, values))

        logger.debug('Cache data: %s', lookup)
        raise gen.Return(lookup)

    @gen.coroutine
    def incr(self, key, ticks=1):
        counter = yield self.get(key)
        if not counter:
            counter = 0
        assert isinstance(counter, int)
        yield self.set(key, counter + ticks)

    @gen.coroutine
    def prepend(self, key, value, size=1000):
        assert size > 1
        assert key
        val = yield self.get(key)
        if val:
            arr = collections.deque(val, maxlen=size)
        else:
            arr = collections.deque(maxlen=size)

        arr.appendleft(value)
        yield self.set(key, list(arr))

    @gen.coroutine
    def append(self, key, value, size=1000):
        assert key
        assert size > 1
        val = yield self.get(key)
        if val:
            arr = collections.deque(val, maxlen=size)
        else:
            arr = collections.deque(maxlen=size)

        arr.append(value)
        yield self.set(key, list(arr))

    @gen.coroutine
    def remove(self, *keys_in):
        if not keys_in:
            pass

        for key in keys_in:
            try:
                del self._cache[key]
            except KeyError:
                pass

    @gen.coroutine
    def flush(self, pattern=None):
        if not pattern:
            raise gen.Return(None)

        logger.debug('Deleting pattern: %s', pattern)

        # turn the simple "star" pattern into a real regex
        pattern = pattern.replace('*', '.*')
        pattern = '%s%s%s' % ('^', pattern, '$')
        matcher = re.compile(pattern)

        keys_to_flush = [key for key in self._cache.keys() if re.match(matcher, key)]
        logger.debug('Flushing cache keys %s', keys_to_flush)
        for key_to_flush in keys_to_flush:
            del self._cache[key_to_flush]

        raise gen.Return(None)

    @gen.coroutine
    def flush_all(self):
        self._cache = dict()
        raise gen.Return(None)
