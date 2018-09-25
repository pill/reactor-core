import logging

production = {
  'cache': {
    'backend': 'reactorcore.services.cache.RedisCache',
    'timeout_seconds': 2
  },
  'debug': True,
  'domain': 'local.reactorcore.com:3000',
  'env': 'development',
  'events': {
    'backend': 'reactorcore.services.event.EventService',
    'polling_interval': 1000 * 10
  },
  'redis': {'host': 'localhost', 'port': 6379, 'db': 0, 'timeout': 5},
  'jobs': {'backend': 'reactorcore.services.jobs.JobService'},
  'secret': 'pZAotJsfAZ/MHTxm6qg4mRRdbXK8RsaLC8LHHHXtNHk=',
}


