from optparse import OptionParser
from tornado import gen, ioloop


from reactorcore import application
from reactorcore.settings import conf

# you could pass your own routes, services, conf here
# #services = { k:v for k,v in services.iteritems() }
application.configure(conf)

parser = OptionParser()
parser.add_option("-d", "--dry-run", dest="dry_run", default="True")

options, _ = parser.parse_args()


@gen.coroutine
def print_services():
    print("Services:")
    print("-------------------")
    app = application.get_application()
    for k in app.service.__dict__.keys():
        if not k.startswith("__") and k not in ["base"]:
            print(k)


if __name__ == "__main__":
    ioloop.IOLoop.instance().run_sync(print_services)
