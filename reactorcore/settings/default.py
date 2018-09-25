import logging
import socket
import os

from reactorcore.settings.version import version

default = {
  'app_name': 'A Microservice',
  'application': {'port': 3000},
  'cache': {
    'backend': 'reactorcore.services.cache.RedisCache',
    'timeout_seconds': 2
  },
  'cron': {
    'backend': 'reactorcore.services.scheduler.SchedulerService',
    'polling_interval': 1000 * 60,
    'tasks': [
        {
            "name" : "example",
            "module" : "reactorcore.cron.example",
            "class" : "ExampleTask",
            "args" : [],
            "kwargs" : {"time_zone": "US/Eastern"},
            "schedule" : {
                "month" : "",
                "day" : "",
                "hour" : "",
                "minute" : "*/2"
            }
        }
    ]
  },
  'debug': True,
  'domain': 'local.reactorcore.com:3000',
  'env': 'development',
  'events': {
    'backend': 'reactorcore.services.event.EventService',
    'polling_interval': 1000 * 10
  },
  'host': socket.gethostname(),
  'jobs': {'backend': 'reactorcore.services.jobs.ImmediateJobService'},
  'locale': 'en_US',
  'redis': {'host': 'localhost', 'port': 6379, 'db': 0, 'timeout': 5},
  'scheme': 'http',
  'secret': 'S5etPPoGLXNAfAyND2cBwPMOuUBstu3bdrKtCYEJ4Ew=',
  'session_cookie_name': 'session',
  'version': version
}
