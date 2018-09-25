test = {
  'cache': {
    'backend': 'reactorcore.services.cache.MemoryCache',
    'timeout_seconds': 2
  },
  'domain': 'local.reactorcore.com:3000',
  'env': 'test',
  'events': {
    'backend': 'tests.integration.services.event.MemoryEventService',
    'polling_interval': 1000 * 10
  },
  'redis': {'host': 'localhost', 'port': 6379, 'db': 0, 'timeout': 5},
  'jobs': {'backend': 'reactorcore.services.jobs.ImmediateJobService'},
  'secret': 'BKOJRQ1mqVX3K548cr8srOOXI2JBmv7Y66ZqqGaWRPc=',
}
