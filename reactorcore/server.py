# pylint: disable=invalid-name
import os

import tornado.httpserver
import tornado.ioloop

from reactorcore import application
from reactorcore import urls
from reactorcore import services

def start_server(app=None):
    """
    Starts server with `app` passed in which may
    be configured with custom conf, routes, and services.

    Starts polling for `deferred events` and `scheduled jobs`.
    """

    if not app:
        from reactorcore.settings import conf
        application.configure(conf)
        app = application.get_application()

    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(app.conf['application']['port'])

    # event polling
    tornado.ioloop.PeriodicCallback(
        app.service.event.queue_ready_events,
        app.conf['events']['polling_interval']
    ).start()

    # cron scheduled jobs check
    tornado.ioloop.PeriodicCallback(
        app.service.scheduler.check_scheduled_tasks,
        app.conf['cron']['polling_interval']
    ).start()

    loop = tornado.ioloop.IOLoop.instance()
    loop.start()

if __name__ == "__main__":
    start_server()