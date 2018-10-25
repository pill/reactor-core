# Reactor Core
## A micro service framework built on Tornado and RQ

![](docs/images/simpsons_radioactive.jpg)

## More Detailed docs

- [Local Docker setup](docs/local-docker.md)
- [Cron](docs/cron.md)
- [Events](docs/events.md)
- [Jobs](docs/jobs.md)
- [Cache](docs/cache.md)

## Local Setup
### Install virtualenv and virtualenvwrapper
[virtualenv](https://pypi.python.org/pypi/virtualenv)
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)

### Get homebrew (if you don't already have it)
[homebrew](https://brew.sh/)

### Install redis-server
```
brew install redis
```

### Create virtualenv for Python
```
virtualenv reactorcore
pip install -e reactor-core
```

## Start Redis
### Run Redis Server
```
redis-server
```


## Install
```
pip install -r requirements.txt
```

If you get an error installying pycurl try:
```
PYCURL_SSL_LIBRARY=openssl LDFLAGS="-L/usr/local/opt/openssl/lib" CPPFLAGS="-I/usr/local/opt/openssl/include" pip install --no-cache-dir pycurl
```


## Start server
```
python -m reactorcore.server
```

## Run tests
```
nosetests tests
```

# Extending Reactor Core
When you configure the application for your service, you can can extend `conf`,
`routes`, and `services`.

Example
```py
from reactorcore import application
from reactorcore.settings import conf
from reactorcore.server import start_server

from myapp.transform.urls import routes
from myapp.transform.services import something

def main():

    # override conf settings
    # and add a cron task
    conf['cron']['tasks'] = [
        {
            "name" : "demotask",
            "module" : "myapp.transform.cron.demo",
            "class" : "DemoTask",
            "args" : [],
            "kwargs" : {"time_zone": "US/Eastern"},
            "schedule" : {
                "month" : "",
                "day" : "",
                "hour" : "",
                "minute" : "*/1"
            }
        }
    ]

    # services
    transform_services = {
        'transform' : something.TextTransform()
    }

    # add custom conf, routes, and services
    application.configure(conf, routes=routes, services=transform_services)
    start_server(application.get_application())

if __name__ == "__main__":
    main()

```

## Automated Docker image builds
Whenever a commit is tagged using regular `Git` tags, Travis will build a new Docker image and push it to
the Docker repository using the current tag. The convention for this repository
is to a major.minor versioning scheme, e.g. `1.9`, `1.10` etc.

### Tagging a commit
To tag a commit locally, run this command (using tag 1.20 as the example):
```
git tag 1.20
```

### Pushing a tag to the remote repo
To push a single tag to a remote repo, run this command (using tag 1.20 as the example):
```
git push origin 1.20
```
To push all tags to the remote repo, use the `--tags` parameter:
```
git push origin --tags
```

## Reactor Core Services

### Cron (scheduled tasks)
A distributed CRON. You can schedule tasks to happen periodically (hourly, daily...). The cron task definition lives on every instance of your app you have, and the task will still only run once as scheduled.
[Cron documentation](docs/cron.md)

### Events (aka Deferred Events)
You can schedule something to happen a certain amount of time in the future. For example, after you create a token you may want it to expire in 24 hours, that would be a good use case for this. Or you want to implement reminder notifications that occur after a requested amount of time.
[Events documentation](docs/events.md)

### Jobs (using a worker queue)
Jobs are tasks that are put on a job queue (built on [the Redis based RQ](http://python-rq.org/)) to be processed as they come in but asynchronously. This is good for big batch operations or heavier computations. It also allows you to throw more "workers" at the queue to process it quicker.
[Jobs documentation](docs/jobs.md)

### Cache
Cache is a Redis based standard cache. You can put values here and set a TTL to indicate when the cached item should invalidate.
[Cache documentation](docs/cache.md)
