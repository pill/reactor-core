class Env(object):
    TEST = "test"
    DEV = "development"
    INT = "integration"
    QA = "qa"
    PROD = "production"

    ALL = [TEST, DEV, INT, QA, PROD]


class Event:
    DATA = "data"
    GROUP = "group"
    HANDLER = "handler"
    READY_AFTER = "ready_after"
    CREATED_AT = "created_at"


class Jobs(object):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
