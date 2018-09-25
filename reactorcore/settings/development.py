development = {
  'cache': {
    'backend': 'reactorcore.services.cache.RedisCache',
    'timeout_seconds': 2
  },
  'env': 'development',
  'events': {
    'backend': 'reactorcore.services.event.EventService',
    'polling_interval': 1000 * 10
  },
  'jobs': {'backend': 'reactorcore.services.jobs.ImmediateJobService'},
  'redis': {'host': 'localhost', 'port': 6379, 'db': 0, 'timeout': 5},
  'secret': 'Coj5y6mT6yhC8OeJ2UIcaBNdwmK5PYq6HLs0Ngbyf4E=',
}
