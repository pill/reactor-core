from __future__ import absolute_import
import logging
from concurrent.futures import ThreadPoolExecutor
import redis
import multiprocessing
from reactorcore import application

logger = logging.getLogger(__name__)
conf = application.get_conf()


class RedisSource(object):
    _redis = None

    def __init__(self, name, cls):
        self.name = name
        self.executor = ThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count()
        )
        self.cls = cls

    @property
    def client(self):
        if RedisSource._redis is None:
            logger.debug("Connecting to Redis, params: %s", conf["redis"])
            redis_conf = conf["redis"]
            try:
                RedisSource._redis = redis.Redis(
                    host=redis_conf["host"],
                    port=redis_conf["port"],
                    db=redis_conf["db"],
                    socket_timeout=redis_conf["timeout"],
                    socket_keepalive=True,
                )

            except redis.RedisError as ex:
                logger.critical("Could not connect to Redis: %s", ex)

        return RedisSource._redis
