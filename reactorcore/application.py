import os
import logging
import importlib
import json

from tornado import web, escape
from tornado.ioloop import IOLoop

from reactorcore import constants
from reactorcore import services
from  reactorcore import urls
from reactorcore import util

logger = logging.getLogger(__name__)

# patch json encoding
def json_encode(value):
    return json.dumps(
        value,
        default=util.datetime_handler).replace("</", "<\/")
escape.json_encode = json_encode


class Application(web.Application):

    conf = None

    def __init__(self, conf, routes=None, services=None):
        # conf MUST be passed in upon creation
        assert conf, 'conf is required'
        self.conf = conf
        routes = routes or []
        services = services or util.AttributeDict()

        here = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        settings = dict(
            template_path=os.path.join(here, "templates"),
            debug=conf['debug'],
            xsrf_cookies=False,
            cookie_secret=conf['secret'],
            compress_response=True,
            autoescape=None
        )

        # possible extended routes
        all_routes = urls.routes + routes

        super(Application, self).__init__(all_routes, **settings)

        self.env = conf['env']

        # set shortcut to environment
        self.is_dev = (self.env == constants.Env.DEV)
        self.is_test = (self.env == constants.Env.TEST)
        self.is_prod = (self.env == constants.Env.PROD)

        self.service = util.AttributeDict()

        self.service.jobs = self._get_instance_from_name(
            conf['jobs']['backend'])
        self.service.scheduler = self._get_instance_from_name(
            conf['cron']['backend'])
        self.service.event = self._get_instance_from_name(
            conf['events']['backend'])
        self.service.cache = self._get_instance_from_name(
            conf['cache']['backend'])

        # possible extended services
        for service_name, service in services.items():
            setattr(self.service, service_name, service)

        logger.info(
            'Reactor started, env %s, jobs %s, cron %s, events %s, cache %s',
            self.env,
            conf['jobs']['backend'],
            conf['cron']['backend'],
            conf['events']['backend'],
            conf['cache']['backend'])

    def _get_instance_from_name(self, class_path, *args, **kwargs):
        module_names = class_path.split('.')
        module_path = '.'.join(module_names[:-1])
        class_name = module_names[-1]

        module = importlib.import_module(module_path)
        class_ = getattr(module, class_name)
        return class_(*args, **kwargs)

# Singletons, one of each per running reactorcore
_app = None
_conf = None
_routes = []
_services = {}

def configure(conf, routes=None, services=None):
    """
    This must be called before creating application.
    It is the global configuration for the Application.
    """
    global _conf
    global _routes
    global _services
    routes = routes or []
    services = services or {}
    _conf, _routes, _services = conf, routes, services

def get_application():
    global _app
    assert _conf, 'application not configured yet, call configure(conf) first'
    if not _app:
        # create with current configuration
        _app = Application(conf=_conf, routes=_routes, services=_services)
    return _app

def get_conf():
    # get the conf that is configured on the current running app
    global _conf
    assert _conf, 'application not configured yet, call configure(conf) first'
    return _conf
