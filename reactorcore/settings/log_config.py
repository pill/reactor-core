import os
import socket
import copy

from reactorcore.constants import Env

hostname = socket.gethostname()

HANDLERS = {
    "console": {
        "class": "logging.StreamHandler",
        "level": "DEBUG",
        "formatter": "generic",
        "stream": "ext://sys.stdout",
    },
    "syslog": {
        "class": "logging.handlers.SysLogHandler",
        "level": "DEBUG",
        "address": ("10.0.0.146", 1514),
        "facility": 19,
        "formatter": "generic",
    },
    "null": {"class": "logging.NullHandler"},
}
FORMATTERS = {
    "generic": {
        "format": "[{0} PID {1}] %(asctime)s %(levelname)-8.8s %(name)s:%(lineno)d | %(message)s".format(
            hostname, os.getpid()
        )
    }
}

BASE_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": HANDLERS,
    "formatters": FORMATTERS,
    "loggers": {
        "": {"level": "DEBUG", "handlers": ["console"]},
        "tornado": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": 0,
        },
        "tornado.access": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": 0,
        },
        "reactorcore": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": 0,
        },
        "reactorcore.handler.base": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": 0,
        },
        "reactorcore.dao": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": 0,
        },
        "reactorcore.dao.event": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": 0,
        },
        "reactorcore.dao.redis": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": 0,
        },
        "reactorcore.services.cache": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": 0,
        },
    },
}

# console
CONSOLE = copy.deepcopy(BASE_CONFIG)

# syslog
SYSLOG = copy.deepcopy(BASE_CONFIG)
map(
    lambda logger: logger.update({"handlers": ["syslog"]}),
    SYSLOG["loggers"].values(),
)
SYSLOG["loggers"]["reactorcore.dao"]["level"] = "WARNING"

# both
CONSOLE_AND_SYSLOG = copy.deepcopy(BASE_CONFIG)
map(
    lambda logger: logger.update({"handlers": ["console", "syslog"]}),
    CONSOLE_AND_SYSLOG["loggers"].values(),
)

ALL = {
    Env.INT: CONSOLE_AND_SYSLOG,
    Env.PROD: SYSLOG,
    Env.QA: CONSOLE_AND_SYSLOG,
    Env.TEST: CONSOLE,
    Env.DEV: CONSOLE,
}
