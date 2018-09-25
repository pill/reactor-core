from tornado.web import URLSpec
from tornado.web import StaticFileHandler

routes = [
    # routes
    URLSpec(r"/", "reactorcore.handlers.index.Index", name="index"),

    # static files
    URLSpec(r"/(favicon.ico)",
            StaticFileHandler,
            {"path": "./reactorcore/assets/favicon"})
]
