"""
Basic distributed scheduling mechanism with Tornado and Redis

    - looks at `cron` setting in settings.py
    - checks to see which tasks are ready to run
    - uses tornado-redis for locking
    - runs each `CronTask` as a separate Subprocess

example settings:

    environment['cron']['tasks'] = [
        {
            'name' : 'test_task',
            'module' : 'cron.tasks.test',
            'class' : 'TestTask',
            'args' : ['arg1'], # args to the `execute` method CronTask
            'kwargs' : {'kwarg1' : 'nil'}, # kwargs
            'schedule' : {
                'month' : '',
                'day' : '',
                'hour' : '',
                'minute' : '*/1'
            }
        },
    ]

"""
import datetime
import logging
import functools
import os
import time
import copy
import sys
import traceback
import multiprocessing
from importlib import import_module

from tornado import concurrent
from tornado import gen
import tornado.process

from reactorcore.dao.redis import RedisSource
from reactorcore.services.base import BaseService
from reactorcore import application
from reactorcore.exception import CronError

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
conf = application.get_conf()

class VoidSchedulerService(BaseService):
    @gen.coroutine
    def check_scheduled_tasks(self):
        pass

    def get_task_by_name(self, task_name):
        for t in conf['cron']['tasks']:
            if task_name == t['name']:
                return t
        return None

class SchedulerService(RedisSource, BaseService):
    _initialized = False

    @staticmethod
    def initialize():
        if SchedulerService._initialized:
            logger.debug(
                'Trying to initialize the SCHEDULER service more than once')
            return

        SchedulerService._initialized = True

    def __init__(self):
        super(SchedulerService, self).__init__(name='SCHEDULER',
                                               cls=self.__class__)
        self.initialize()
        self._locks = {}
        self.executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())

    def get_task_by_name(self, task_name):
        for t in conf['cron']['tasks']:
            if task_name == t['name']:
                return self._copy_task(t)
        return None

    def _is_ready(self, s_val, n_val):
        """
        Check scheduled val (s_val) vs now val (n_val)
        """
        # it's ok for some frequency values to not be set
        # (assumes at least one is set)
        if not s_val:
            return True

        # eg. format for every 5 minutes = */5
        if '/' in s_val:
            chunks = s_val.split('/')
            if len(chunks) == 2 and chunks[0] == '*':
                s_val, n_val = int(chunks[1]), int(n_val)
                return n_val % s_val == 0
        else:
            # standard exact digit match format
            return int(n_val) == int(s_val)
        return False

    @gen.coroutine
    def redis_now(self):
        """
        All reactors should use the clock from the Redis machine
        """
        redis_time = self.client.time()
        raise gen.Return(datetime.datetime.fromtimestamp(redis_time[0]))

    @gen.coroutine
    def find_ready_tasks(self):
        n = yield self.redis_now()
        n_times = [n.month, n.day, n.hour, n.minute]
        logger.debug("Redis time: %s %s %s:%s",
                     n.month, n.day, n.hour, n.minute)

        ready_tasks = []

        for task in conf['cron']['tasks']:

            task = self._copy_task(task)

            logger.debug('Checking CRON task: %s', task)
            s = task['schedule']
            task['name'] = 'cron:' + task['name']
            s_times = [s.get('month'),
                       s.get('day'),
                       s.get('hour'),
                       s.get('minute')]
            logger.debug('Task time:  %s %s %s:%s',
                         s_times[0], s_times[1], s_times[2], s_times[3])

            # skip entry that has unset time constraints
            if not any(s_times):
                logger.error(
                    'Set at least one time constraint for cron schedule')
                continue

            # if all time constraints for task OK, then it's ready
            if all([self._is_ready(t, n_times[count])
                        for count, t in enumerate(s_times)]):
                logger.debug('Scheduled task ready: %s', task)
                ready_tasks.append(task)
            else:
                logger.debug('Task NOT ready')

        raise gen.Return(ready_tasks)

    def _copy_task(self, task):
        # make copy, deepcopy creates unpickleable object
        ctask = task.copy()
        ctask['schedule'] = task['schedule'].copy()
        ctask['kwargs'] = task['kwargs'].copy()
        ctask['args'] = task['args'][:]
        return ctask

    def get_min_ttl(self, task):
        # TODO time will be lowest frequency block for cycle
        if task['schedule'].get('minute'):
            return 60
        if task['schedule'].get('hour'):
            return 60 * 60
        if task['schedule'].get('day'):
            return 60 * 60 * 24
        if task['schedule'].get('month'):
            return 60 * 60 * 24 * 31
        raise CronError('Set at least one time constraint for cron schedule')

    def _acquire_lock(self, task):
        """
        Acquire lock to run a task on reactorcore
        """
        logger.debug('Getting lock for cron task %s"', task)
        min_ttl = self.get_min_ttl(task)
        logger.debug('Min TTL: %s', min_ttl)

        # make sure we are using the exact same lock object
        # client.lock() will overwrite it
        if task['name'] in self._locks:
            task_lock = self._locks[task['name']]
        else:
            task_lock = self.client.lock(
                task['name'],
                timeout=min_ttl,
                sleep=1
            )
            self._locks[task['name']] = task_lock

        # returns a Future
        return task_lock.acquire(blocking=False)

    @gen.coroutine
    def _release_lock(self, *args):
        """
        Release the lock for a task
        args = (task, start_time)
        """
        logger.debug('Releasing lock')
        task, start_time = args[0], args[1]
        min_ttl = self.get_min_ttl(task)
        end_time = time.time()
        total_run_time = end_time - start_time
        logger.debug('Total run time: %s', total_run_time)

        if total_run_time < min_ttl:
            logger.debug('Skip releasing lock ended(%s) < min_ttl(%s)',
                         end_time, min_ttl)
        else:
            task_lock = self._locks[task['name']]
            logger.debug('Found task lock to release: %s', task_lock)
            res = yield gen.Task(self.task_lock.release)
            logger.debug('Lock released? %s', res)
            res = yield gen.Task(self.task_lock.release)

    @concurrent.run_on_executor
    def run_task_process(self, task, callback):
        try:
            task_callable = self._get_callable(task['name'])
            task_callable()
        except Exception as ex:
            _, ex, tb = sys.exc_info()
            tb = traceback.extract_tb(tb)
            stacktrace = traceback.format_list(tb)
            logger.critical('[EXCEPTION] Could not create subprocess, %s: %s',
                            stacktrace, ex.message, exc_info=True)

    def _get_callable(self, task_name):
        task_info = self._get_task_info(task_name)
        if not task_info:
            raise Exception('No task defined for task_name: `{}`'.format(
                task_name))

        module_str = task_info['module']
        class_str = task_info['class']

        module = import_module(module_str)
        cls = getattr(module, class_str)

        args = task_info.get('args', [])
        # pass class def as first arg
        args.insert(0, cls())
        kwargs = task_info.get('kwargs', {})

        # pass an instance of app
        kwargs['app'] = application.get_application()

        # bake in args and kwargs
        partial = functools.partial(cls.execute, *args, **kwargs)

        return partial

    def _get_task_info(self, task_name):
        for task in conf['cron']['tasks']:
            if 'cron:' + task['name'] == task_name:
                return self._copy_task(task)

    @gen.coroutine
    def check_scheduled_tasks(self):
        """
        Checks settings for cron_schedule (environment['cron']['tasks'])
        for tasks to run
        """

        # TODO: there's a bug if task is scheduled every minute */1

        logger.debug('Checking for scheduled tasks')

        ready_tasks = yield self.find_ready_tasks()
        for task in ready_tasks:
            logger.debug('Task is %s', task)
            lock_res = self._acquire_lock(task)
            logger.debug('Acquire lock result: %s', lock_res)
            if lock_res:
                start_time = time.time()
                yield self.run_task_process(
                    task,
                    functools.partial(self._release_lock, *[task, start_time])
                )
