from reactorcore.handlers.base import BaseRequestHandler


class Index(BaseRequestHandler):
    def get(self):
        self.render("index.html")
