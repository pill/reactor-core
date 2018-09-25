from __future__ import absolute_import
import logging

from redis.exceptions import RedisError
from rq import Queue
from tornado import concurrent
from tornado import gen

from reactorcore.dao import redis
from reactorcore.util import gen_random_string

logger = logging.getLogger(__name__)


@gen.coroutine
def im_wrapper(*args, **kwargs):
    """
    Make instance method pickleable by pickling the class and function name
    instead of the instance method

    where:
        cls = the class
        f_name = function name

    This will get called by RQ upon unpickling

    """
    cls = kwargs.pop('cls')
    f_name = kwargs.pop('f_name')
    im = getattr(cls(), f_name)
    res = yield im(*args, **kwargs)
    raise gen.Return(res)


class Jobs(object):
    HIGH = 'high'
    NORMAL = 'normal'
    LOW = 'low'


class JobService(redis.RedisSource):
    def __init__(self):
        super(JobService, self).__init__(name='JOBS', cls=self.__class__)

    def is_async(self):
        return True

    def _get_queue(self, priority=None):
        priority = priority or Jobs.NORMAL
        return Queue(priority, connection=self.client, async=self.is_async())

    @gen.coroutine
    def add(self, func=None, args=None, kwargs=None, priority=None, depends_on=None):
        args = args or ()
        kwargs = kwargs or {}

        job_id = gen_random_string(size=6)

        # if synchronous - just run the function in the same thread
        if not self.is_async():
            yield func(*args, **kwargs)
            raise gen.Return(None)

        yield self._add(
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            depends_on=depends_on,
            job_id=job_id
        )

        logger.debug('Added job id(%s) to queue', job_id)
        raise gen.Return(None)

    @concurrent.run_on_executor
    def _add(self, *args, **kwargs):
        job_id = kwargs['job_id']
        priority = kwargs['priority']
        func = kwargs['func']
        f_args = kwargs['args']
        f_kwargs = kwargs['kwargs']
        depends_on = kwargs['depends_on']
        priority = priority or Jobs.NORMAL

        logger.debug('Adding JOB "%s" on %s', func.__name__, priority)

        q = self._get_queue(priority)

        # these are for the wrapper
        f_kwargs['cls'] = func.im_class
        f_kwargs['f_name'] = func.__name__

        res = None
        try:
            res = q.enqueue_call(
                func=im_wrapper,
                args=f_args,
                kwargs=f_kwargs,
                depends_on=depends_on
            )

        except RedisError, ex:
            logger.critical('[EXCEPTION] Error adding job id(%s) %s',
                            job_id, ex.message, exc_info=True)

            res = None

        return res


class ImmediateJobService(JobService):
    """Job queue class that forces sync run for scheduled tasks.
       Useful in development, testing, or where there is no Redis
       environment."""

    def is_async(self):
        return False
