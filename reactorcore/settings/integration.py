integration = {
    "cache": {
        "backend": "reactorcore.services.cache.RedisCache",
        "timeout_seconds": 2,
    },
    "env": "integration",
    "events": {
        "backend": "reactorcore.services.event.EventService",
        "polling_interval": 1000 * 10,
    },
    "jobs": {"backend": "reactorcore.services.jobs.JobService"},
    "redis": {"host": "localhost", "port": 6379, "db": 0, "timeout": 5},
    "secret": "PCeUm+R5WJf0nBpq4mmJSKyqddmO9zV2Nji+jcUIBdM=",
}
