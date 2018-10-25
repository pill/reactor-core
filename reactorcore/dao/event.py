from __future__ import absolute_import

import logging
import json
import time
import copy

from tornado import concurrent
from redis.exceptions import RedisError

from reactorcore import models
from reactorcore import util
from reactorcore.dao import redis

logger = logging.getLogger(__name__)


class EventDao(redis.RedisSource):
    def __init__(self):
        super(EventDao, self).__init__(name="EVENT", cls=self.__class__)
        self.prefix = "event:"

    @concurrent.run_on_executor
    def create_event(self, e, group_by=None):
        """
        Create an event that will eventually expire and be processed
        by an event handler.

        "group_by" is any client-supplied unique string that will
        be used to bundle multiple events to be processed at once.
        (Example: user gets one combined email about comments on their
         post in the last hour)
        """

        logger.debug("Creating event %s", e.to_dict())

        assert e.ready_after is not None
        assert e.handler
        assert e.data

        # copy the event object to avoid mutating the original
        event = models.Event(
            handler=e.handler,
            ready_after=e.ready_after,
            data=copy.deepcopy(e.data),
        )

        # for grouped events
        existing_score = None

        group = None

        if group_by:
            """
            Check if an event of this type had been created.
            If so - it has not expired yet, so assign the same score to this new event,
            to make sure all events of the same type expire at once (grouping)
            """
            group = "event:group:{}-{}-{}".format(
                str(group_by), event.handler, event.ready_after
            )

            existing_score = self.client.get(group)
            if existing_score:
                logger.debug(
                    "Events for group %s already exists with score %s",
                    group,
                    existing_score,
                )
                event.score = existing_score
            else:
                event.score = time.time() + event.ready_after
                logger.debug(
                    "NEW score for events in group %s: %s", group, event.score
                )
        else:
            # we are not grouping this event
            event.score = time.time() + event.ready_after
            logger.debug("New UNGROUPED event: %s", event.to_dict())

        event.created_at = str(util.utc_time())

        data = event.to_dict()
        if group_by:
            data["group"] = group

        try:
            json_data = json.dumps(data)
            self.client.zadd("event", json_data, event.score)

            if group_by:
                """
                If this is a new event group - save the score.
                This will help us quickly identify later events
                that fall into the same group - they will expire at once.
                """
                if not existing_score:
                    logger.debug(
                        "Creating event group %s with score %s",
                        group,
                        event.score,
                    )
                    self.client.set(group, event.score)
        except RedisError as ex:
            logger.critical("Error creating event %s, %s", ex.message, event)

        return event

    @concurrent.run_on_executor
    def pop_ready_events(self):
        min_score = 0
        max_score = time.time()

        logger.debug("Getting ready events with max score %s", max_score)

        data = None
        try:
            # get and remove ripe events in one swoop
            pipe = self.client.pipeline(transaction=True)
            pipe.zrangebyscore("event", min_score, max_score)
            pipe.zremrangebyscore("event", min_score, max_score)

            # returns array of results - one for each command in the pipe
            data, _ = pipe.execute()
        except RedisError as ex:
            logger.critical("Error getting events: %s", ex)

        if not data:
            logger.debug("No event data found")
            return []

        events = []
        logger.info("Found %d ripe events", len(data))

        # unique event groups - they expire at the same time
        # and to be deleted once we send these events off to a farm upstate
        event_groups = set()

        for rec in data:
            # load JSON string from Redis
            d = json.loads(rec)
            # create an event object from the JSON dictionary we have
            event = models.Event() << d
            logger.debug("Found event: %s", event.to_dict())
            events.append(event)

            # unique group key for this event, if grouped
            group = d.get("group")
            # add event group (to be deleted later)
            if group:
                logger.debug(
                    "Adding group %s to the set of GROUPS TO BE DELETED", group
                )
                event_groups.add(group)

        if event_groups:
            try:
                logger.debug("Removing event groups: %s", event_groups)
                self.client.delete(*event_groups)
            except RedisError as ex:
                logger.critical("Error deleting event groups", ex)

        return events
