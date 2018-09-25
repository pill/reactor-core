import json
from tornado import gen
from reactorcore.services.event import AbstractEventService
from reactorcore.model import Event


class MemoryEventService(AbstractEventService):

    def __init__(self):
        self.events = list()
        self.processed_events = list()
        self.time = 0  # seconds

    @gen.coroutine
    def queue_ready_events(self):
        events = self._pop_ready_events()
        self.processed_events.extend(events)
        yield self.process_events(events=events)

    def _pop_ready_events(self):
        ready = filter(
            lambda (created_at, e): self.time - created_at >= e.ready_after, self.events)
        self.events = filter(
            lambda (created_at, e): self.time - created_at < e.ready_after, self.events)
        ready_events = [e[1] for e in ready]

        return ready_events

    @gen.coroutine
    def create_event(self, event, group_by=None):
        # copy
        e = Event().from_dict(event.to_dict())

        # fake json serializing to ensure serialization works
        json.dumps(e.data)

        e.group = group_by
        self.events.append((self.time, e))

    def forward_time_by(self, seconds):
        self.time = self.time + seconds
