import time
from reactorcore.cron.base import CronTask


class ExampleTask(CronTask):
    def execute(self, *args, **kwargs):
        print("")
        print("Executing Cron ExampleTask!")
        print("")
