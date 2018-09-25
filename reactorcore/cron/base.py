from tornado import gen

class CronTask(object):
    @property
    def app(self):
        from reactorcore import application
        return application.get_application()

    @gen.coroutine
    def execute(self, *args, **kwargs):
        """
        `app` will be passed as a kwarg
        """
        raise NotImplementedError()