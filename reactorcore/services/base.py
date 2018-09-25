from tornado import gen

class BaseService(object):

    @property
    def app(self):
        from reactorcore import application
        return application.get_application()

