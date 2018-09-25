import logging
import logging.config
import json
import os

from reactorcore.constants import Env
from reactorcore.settings import log_config

from .default import default as conf
from .test import test
from .development import development
from .integration import integration
from .qa import qa
from .production import production

logging.basicConfig(level=logging.DEBUG)

configs = {Env.INT: integration,
           Env.TEST: test,
           Env.QA: qa,
           Env.PROD: production,
           Env.DEV: development}

# when env is not set, assume it's a local development instance
env = os.getenv("ENV", "development").lower()

if env not in Env.ALL:
    raise EnvironmentError("Unknown ENV value, should be one of %s", Env.ALL)

# If an environment variable is set in the form of REDIS_[KEY],
# use it instead of the defaults.
def replace_redis(key, v):
    try:
        env_variable = "_".join(["REDIS", key.upper()])
        return os.environ[env_variable]
    except KeyError:
        return v
configs[env]['redis'] = {k:replace_redis(k, v) for k, v in configs[env]['redis'].items()}

conf.update(configs[env])

# load periodic tasks config
#crontab = "cron_jobs_prod.json" if env == Env.PROD else "cron_jobs_dev.json"
#
#crontab_path = os.path.abspath(
#    os.path.join(os.path.dirname(__file__), "../settings/cron", crontab))

#with open(crontab_path) as json_file:
#    conf["cron"]["tasks"] = json.load(json_file)

# configure logging
log_settings = log_config.ALL[env]

logging.config.dictConfig(log_settings)