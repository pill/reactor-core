# Extending Reactor Core
When you configure the application for your service, you can can extend `conf`,
`routes`, and `services`. These must be passed to `application.configure` before starting the server.

Example `server.py`
```py
from reactorcore import application
from reactorcore.server import start_server

import os
import datetime

from my_project.api.settings import conf
from my_project.api.urls import routes
from my_project.api.services import topics

my_project_services = {
    'topics' : topics.TopicsService(),
}

# use docker redis container
conf['redis']['host'] = os.getenv('REDIS_HOST', 'redis')

def main():
    # add custom conf, routes, and services
    application.configure(conf, routes=routes, services=my_project_services)
    start_server(application.get_application())

if __name__ == "__main__":
    main()
```

## Configuration

## Routes

## Services
