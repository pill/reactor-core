import copy
import json
import logging
import string
import urllib
import httplib
import traceback

from datetime import timedelta

from pymongo import MongoClient

from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPClient
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.testing import AsyncTestCase, bind_unused_port

from reactorcore import application, constants, util, model
from reactorcore.script.update_indexes import evolutions

from tests.factories.user import UserFactory
from tests.factories.item import ItemFactory
from tests.factories.comment import CommentFactory

logger = logging.getLogger(__name__)
conf = application.get_conf()

class IntegrationTestCase(AsyncTestCase):
    """
    Tornado Async Test Case, but with our helper methods
    """

    def get_app(self):
        return application.get_application()

    def setUp(self):

        # reset events service
        setattr(self.app.service.event, 'app', self.app)

        self.app.service.event.events = []
        self.app.service.event.processed_events = []
        self.app.service.event.time = 0  # seconds

        super(IntegrationTestCase, self).setUp()

        # clear cache
        self.app.service.cache._cache = {}
        self.app.service.cache.hits = 0
        self.app.service.cache.misses = 0

    # otherwise, we will run on a different ioloop, and all tests will hang!
    def get_new_ioloop(self):
        return IOLoop.instance()

class HttpIntegrationTestCase(IntegrationTestCase):
    """
    Heavily modified version of Tornado's AsyncHTTPTestCase,
    but we spawn the server and client *once*, for each test class,
    as opposed to every single test.
    """
    FORM = 'application/x-www-form-urlencoded'
    JSON = 'application/json'
    GET = 'GET'
    POST = 'POST'
    DELETE = 'DELETE'
    COOKIE = 'Cookie'
    SET_COOKIE = 'Set-Cookie'

    def setUp(self):
        super(HttpIntegrationTestCase, self).setUp()
        sock, port = bind_unused_port()
        self.port = port

        self.http_server = self.get_http_server()
        self.http_server.add_sockets([sock])

        self.http_client = self.get_http_client()
        self.result = None

        xsrf_token_url = self.app.reverse_url('api.token')
        xsrf_token_response = self.fetch(xsrf_token_url)
        data = json.loads(xsrf_token_response.body)
        self.token = data[constants.Api.TOKEN]

    def get_auth_header(self, data):
        return {
            'X-XSRFToken': self.token,
            'Cookie': '_xsrf={0}'.format(self.token)}

    def tearDown(self):
        super(HttpIntegrationTestCase, self).tearDown()
        if (not IOLoop.initialized() or self.http_client.io_loop is not IOLoop.instance()):
            self.http_client.close()
        self.http_server.stop()

    def get_http_client(self):
        return AsyncHTTPClient(io_loop=IOLoop.instance())

    def get_http_server(self):
        return HTTPServer(self.app, io_loop=IOLoop.instance())

    def fetch(self, path, **kwargs):
        """Convenience method to synchronously fetch a url.

        The given path will be appended to the local server's host and
        port.  Any additional kwargs will be passed directly to
        `.AsyncHTTPClient.fetch` (and so could be used to pass
        ``method="POST"``, ``body="..."``, etc).
        """
        self.http_client.fetch(self.get_url(path), self.stop, **kwargs)
        return self.wait()

    def get_url(self, path):
        """Returns an absolute url for the given path on the test server."""
        return '%s://localhost:%s%s' % ('http', self.port, path)

    def http(self, loc, method, expect_code=httplib.OK, data=None, content_type=None,
             headers=None, follow_redirects=True):
        """Makes a HTTP call."""

        data = copy.deepcopy(data) or {}
        headers = headers or self.get_auth_header(data)

        if content_type:
            headers['Content-Type'] = content_type

        body = None

        if method == self.POST and content_type == self.FORM:
            body = urllib.urlencode(data)
        elif content_type == self.JSON:
            body = json.dumps(data)

        self.result = self.fetch(
            loc, method=method, body=body, headers=headers, follow_redirects=follow_redirects)
        self.assertEqual(self.result.code, expect_code)

        return self.result
