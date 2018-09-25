# CRON
Reactor core lets you schedule tasks to run periodically according to the `cron` field in your 
settings file. You should subclass `reactorcore.cron.base.CronTask` and implement the `execute()`
method. The task will run on a worker reactor-core, as not to block the app.

example `CronTask`
```
import time
from reactorcore.cron.base import CronTask


class ExampleTask(CronTask):

    def execute(*args, **kwargs):
        print ''
        print 'Executing Cron ExampleTask!'
        print ''

```


## CRON settings
In the app settings, you can define `cron` settings.

example cron settings
```
  'cron': {
    'backend': 'reactorcore.services.scheduler.SchedulerService',
    'polling_interval': 1000 * 60,
    'tasks': [
        {
            "name" : "example",
            "module" : "reactorcore.cron.example",
            "class" : "ExampleTask",
            "args" : [],
            "kwargs" : {"time_zone": "US/Eastern"},
            "schedule" : {
                "month" : "",
                "day" : "",
                "hour" : "",
                "minute" : "*/2"
            }
        }
    ]
  }
```

__backend__ - The service that gets called periodically to look for tasks and run them. 
Most likely you would want to use 
`reactorcore.services.scheduler.SchedulerService` but 
it's a setting so that you can mock it out for tests or add custom functionality.

__polling_interval__ - This is how often in milliseconds the scheduler service will 
call `check_scheduled_tasks`.

__tasks__ - A list of tasks to run

_task fields:_

__name__ - The name of the task

__module__ - The module where your task lives

__class__ - The task class

__args__ - List of args to pass to the CronTask

__kwargs__ - Dict of kwargs to pass to the CronTask

__schedule__ - A subset of the standard 

[crontab format](http://www.nncron.ru/help/EN/working/cron-format.htm) 
of when you want the task to run

_schedule fields:_

__month__ - The month of the year when you want the cron to run (1 - 12)

__day__ - The day of the week you want the cron to run (1 - 7, 1 standing for Monday)

__hour__ - The hour you want the cron to run (0 - 23)

__minute__ - The minute you want the cron to run (0-59)



