import logging
from abc import ABCMeta, abstractmethod

from tornado import gen

from reactorcore import util
from reactorcore.dao import event as event_dao
from reactorcore.services import base, jobs

logger = logging.getLogger(__name__)


class AbstractEventService(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def queue_ready_events(self):
        pass

    @abstractmethod
    def create_event(self, event, group_by=None):
        pass

    @gen.coroutine
    def process_events(self, events=None):
        """
        Process events that are ripe as of most recently.
        """
        logger.debug("Processing %s events", len(events))

        """
        Group events by group identifier that is OPTIONALLY
        given with an event object. Groups are used to bundle events
        when saving them in an event repository.
        """
        event_groups = AbstractEventService.group_events(events)

        """
         Any event in group None should be processed separately,
         - these events do not belong to a bundle
        """
        for e in event_groups.pop(None, {}).get("events", []):
            func = self._get_event_handler(e.handler)
            if not func:
                continue
            yield func([e])

        """
        The rest of the groups are not None, they are valid,
        and events in these groups are processed in one go
        """
        for group_id, d in event_groups.items():
            handler = d["handler"]
            grouped_events = d["events"]
            logger.debug("Processing events for group %s", group_id)
            func = self._get_event_handler(handler)
            if not func:
                continue
            yield func(grouped_events)

    @staticmethod
    def group_events(events):
        """
        Determine unique event groups and at the same time
        create a map with ready-to-go arrays for the events.

        We get (example only):

        groups = {
            None: {'events': [e1, e2, e3]},
            'USER-ID-1': {'events': [e1, e2, e3], 'handler': 'COMMENT_ACTIVITY'},
            'USER-ID-2': {'events': [e1, e2, e3, e4], 'handler': 'POST_ACTIVITY'}
        }
        """

        groups = {
            e.group: {"events": [], "handler": e.handler} for e in events
        }

        # allocate the events into their groups
        for e in events:
            groups[e.group]["events"].append(e)

        return groups

    def _get_event_handler(self, handler):
        """
        Dynamically access handler from self.app

        Args:
            handler: a string starting with app. giving the path to handler
            eg.
                'app.service.item_events.item_posted_event_handler'
        """
        assert handler

        obj = self
        for attr in handler.split("."):
            obj = getattr(obj, attr)
        return obj


class EventService(base.BaseService, AbstractEventService):
    def __init__(self):
        super(EventService, self).__init__()

        self.DAO = event_dao.EventDao()
        self._lock = False

    @gen.coroutine
    def queue_ready_events(self):
        if self._lock:
            return

        self._lock = True

        try:
            yield self._queue_ready_events()
        finally:
            self._lock = False

    @gen.coroutine
    def _queue_ready_events(self):
        events = yield self.DAO.pop_ready_events()

        if not events:
            return

        yield self.app.service.jobs.add(
            func=self.process_events,
            kwargs={"events": events},
            priority=jobs.Jobs.NORMAL,
        )

    @gen.coroutine
    def create_event(self, event, group_by=None):
        assert event.handler
        assert event.data
        assert event.ready_after is not None

        logger.debug("Creating event %s group by %s", event, group_by)

        event = yield self.DAO.create_event(event, group_by=group_by)
        raise gen.Return(event)

    def _get_event_handler(self, handler):
        """
        Dynamically access handler from self.app

        Args:
            handler: a string starting with app. giving the path to handler
            eg.
                'app.service.item_events.item_posted_event_handler'
        """
        assert handler

        obj = self
        for attr in handler.split("."):
            obj = getattr(obj, attr)
        return obj

    @util.job
    @gen.coroutine
    def process_events(self, events=None):
        # same as base event service, but in a worker pool
        yield super(EventService, self).process_events(events=events)


class ImmediateEventService(EventService):
    """
    Processes events as they arrive, storing them in a global
    container, to possibly verify that they fire.
    """

    events = []

    @gen.coroutine
    def create_event(self, event, group_by=None):
        assert event.data
        assert event.ready_after is not None

        self.events.append(event)

        logger.debug("Immediately processing event %s", event)
        yield self.process_events(events=[event])


class VoidEventService(EventService):
    """
    Disable events. Useful for batch scripts that otherwise
    would create events we'd rather not fire
    """

    @gen.coroutine
    def create_event(self, event, group_by=None):
        pass
