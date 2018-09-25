import logging
import traceback
import json

import tornado
from tornado import gen
from reactorcore.handlers import base
from reactorcore import exception
from reactorcore import application
from reactorcore import util
from reactorcore import constants
from reactorcore.exception import ExternalServiceError

logger = logging.getLogger(__name__)
conf = application.get_conf()

class BaseApiHandler(base.BaseRequestHandler):
    """API handler."""
    def __init__(self, application, request, **kwargs):
        super(BaseApiHandler, self).__init__(application, request, **kwargs)
        self.data = {}

    def set_default_headers(self):
        """ CORS, for cross browser requests to the API layer
        https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS#Access-Control-Max-Age
        """
        self.set_header('Content-Type', 'application/json')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Methods', 'POST, PUT, GET')
        self.set_header('Access-Control-Allow-Headers', 'Content-Type, X-NSQ-Auth, X-NSQ-Test')
        self.set_header('Allow', 'POST, PUT, GET, OPTIONS, HEAD')

    def options(self):
        return

    # Tornado override
    @gen.coroutine
    def prepare(self):
        yield super(BaseApiHandler, self).prepare()

        content_type = self.request.headers.get('Content-Type', 'application/json').lower()

        if 'application/json' in content_type and self.request.body:
            try:
                self.data = json.loads(self.request.body)
            except ValueError:
                raise Exception('JSON error')

        elif self.request.arguments:
            request_args = self.request.arguments

            """
            Temporary backward compatibility to convert www-form data into JSON,
            to make API endpoints act like "web" endpoints if needed.
            """
            for key, values in request_args.items():
                if not values:
                    continue
                # if a multi-value array, preserve
                if len(values) > 1:
                    self.data[key] = values
                else:  # a single value
                    self.data[key] = values[0]

        self.log_request()

        # let CORS preflight requests through
        if self.request.method != 'OPTIONS':
            self.authenticate()

    def log_request(self):
        masked_args = self._mask_unsafe_data(self.data)
        logger.info('API request START [id:%s]  %s:%s; DATA: %s',
                    self.request.id, self.request.method,
                    self.request.uri, masked_args)

    def log_request_end(self):
        _id = self.request.id if hasattr(self.request, 'id') else '(no id)'
        logger.info('API request END [id:%s] %s, HTTP %s in %.2fms',
                    _id, self.request.uri, self.get_status(),
                    self.request.request_time() * 1000)

    # Tornado override
    def on_finish(self):
        super(BaseApiHandler, self).on_finish()
        self.log_request_end()

    # Tornado override
    def log_exception(self, typ, value, tb):
        """
        Prevent Tornado from logging "uncaught" exceptions as errors.
        we handle all of it ourselves in `write_error()`.
        """
        pass

    # Tornado override
    def write_error(self, status_code, **kwargs):
        exc_info = kwargs.get('exc_info')
        ex = None
        if exc_info:
            ex = exc_info[1]


        if isinstance(ex, exception.NotFound):
            logger.warning("API request WARNING [%s] for user %s: %s", self.request.id, self.current_user, ex)
            self.set_status(ex.status_code)
            response_data = {
                'form_error': {
                    'message': constants.MSG_NOT_FOUND
                }
            }
            self.write(response_data)
            return

        if isinstance(ex, tornado.web.HTTPError):
            logger.warning(ex)
            self.set_status(ex.status_code)
            return

        if isinstance(ex, ExternalServiceError):
            logger.error(ex)
            self.set_status(ex.status_code)
            return

        # handle 500 errors
        if ex:
            """
            Record the last point of the exception.
            Syslog has the limitation of cutting off at 1000 characters,
            which makes it impossible to know where the stacktrace originated from
            """
            error, ex, last_tb = exc_info[:]
            tb = traceback.extract_tb(last_tb)
            file_name, line, func, failed_code = tb[-1]

            _id = self.request.id if hasattr(self.request, 'id') else '(no id)'
            logger.critical('[EXCEPTION] Request end %s %s %s [%s] for user %s. Error: %s. Occurred at: %s:%s %s() in "%s"',
                            self.request.method, self.request.uri,
                            self.get_status(), _id, self.current_user,
                            ex.message, file_name, line, func, failed_code,
                            exc_info=exc_info)
            return


    @gen.coroutine
    def login(self):
        """
        Executes things that must happen at login
            - converts items pending for user (posted while not logged in)
            - sets session cookies
        """
        self.current_user = yield self.app.service.user.get_by_token(
            self.current_user.token
        )
        gsid = self._get_guest_session_id()

        yield self.convert_pending_items(self.current_user, gsid)
        yield self.convert_pending_comments_and_replies(self.current_user, gsid)
        yield self.convert_pending_favorites(self.current_user, gsid)
        self.set_session_cookies()

    def _get_guest_session_id(self):
        """
        Get or create a guest session id cookie
        """
        guest_session_id = self.get_secure_cookie(
            constants.COOKIE_GUEST_SESSION_ID,
            max_age_days=10 * 365
        )
        if not guest_session_id:
            guest_session_id = util.gen_random_string()
            self.set_secure_cookie(
                constants.COOKIE_GUEST_SESSION_ID,
                guest_session_id,
                expires_days=10 * 365
            )
        return guest_session_id

    def set_session_cookies(self):
        self.set_secure_cookie(constants.User.TOKEN, self.current_user.token, expires_days=10 * 365)

        # TODO: remove these
        # frontend should access /a/account/status instead of cookie
        #
        self.set_cookie(
            constants.User.USERNAME, self.current_user.username,
            expires_days=10 * 365
        )

        if self.current_user.avatar:
            self.set_cookie(
                constants.User.AVATAR,
                self.current_user.avatar,
                expires_days=10 * 365
            )


    def clear_session_cookies(self):
        hitlist = [
            '_xsrf',
            constants.User.TOKEN,
            constants.User.USERNAME,
            constants.User.AVATAR
        ]
        for val in hitlist:
            self.clear_cookie(val)

    def authenticate(self):
        if not conf['api']['authenticate']:
            return

    @property
    def is_mobile(self):
        return bool(int(self.request.headers.get("NSQ-Mobile", 0)))

    def check_xsrf_cookie(self):
        """
            Check presence of our mobile header and bypass XSRF.
            Otherwise, use the tornado XSRF check.
        """
        if self.is_mobile:
            return
        else:
            super(BaseApiHandler, self).check_xsrf_cookie()
