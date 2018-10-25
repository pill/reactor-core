import sys
from redis import StrictRedis
from rq import Queue, Connection, Worker

from reactor import application
from reactor.settings import conf

redis = StrictRedis(
    host=conf["redis"]["host"],
    port=conf["redis"]["port"],
    db=conf["redis"]["db"],
)

with Connection(redis):
    application.get_application()
    qs = map(Queue, sys.argv[1:]) or [Queue()]
    w = Worker(qs)
    w.work()
