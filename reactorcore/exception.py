class CronError(Exception):
    status_code = 500


class ExternalServiceError(Exception):
    status_code = 500


class ForbiddenError(Exception):
    status_code = 403


class NotFound(Exception):
    status_code = 404
