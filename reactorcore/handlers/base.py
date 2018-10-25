import itertools
import time
import logging

import tornado.web
from tornado import gen

from reactorcore import constants
from reactorcore import exception
from reactorcore import util

logger = logging.getLogger(__name__)


class BaseRequestHandler(tornado.web.RequestHandler):
    @property
    def app(self):
        from reactorcore import application

        return application.get_application()
