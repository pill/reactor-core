import logging
import urllib
import hashlib
from datetime import timedelta

from tornado import gen

from reactorcore import constants, util

logger = logging.getLogger(__name__)


class Model(object):
    """Shortcut for to_dict() and from_dict() methods.

        Takes a source object and a destination object, one of which
        MUST be a dictionary, and copy over the values of
        attributes specified in the attribute constants object.

        Constants are defined in const.py

        Note that this utility does not respect inheritance,
        so the caller must explicitly invoke this for
        all attribute constants objects, ie:

        Model.copy(source=data, target=self, attrs=constants.Common)
        Model.copy(source=data, target=self, attrs=constants.User)
        Model.copy(source=data, target=self, attrs=constants.Address)"""

    @staticmethod
    def copy(source=None, target=None, attrs=None):
        # must have one dictionary
        if isinstance(source, dict) == isinstance(target, dict):
            raise ValueError(
                "Either the source or the target must be a dictionary"
            )

        if attrs is None:
            raise ValueError("Must specify attribute constants")

        # get attribute names minus reserved and Python ones
        attr_names = constants.attr_names(attrs)

        # when copying from model to dictionary
        if target.__class__.__name__ == "dict":
            data = util.select(source.__dict__, attr_names)
            target.update(data)
        # copying from dictionary to model
        else:
            data = util.select(source, attr_names)
            target.__dict__.update(data)

    def __init__(
        self, id=None, is_clean=False, created_at=None, updated_at=None
    ):
        self.id = id
        self.is_clean = is_clean
        self.created_at = created_at
        self.updated_at = updated_at

    def __str__(self):
        return "<Model: %s>" % self.__dict__

    # type id can be used for search indexing, audit, etc
    def type_id(self):
        return self.__class__.__name__.lower()

    # equality is based on object ID
    def __eq__(self, other):
        if other == None:
            return self.id == None

        return self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    # update model properties from a dictionary
    def update(self, data):
        # NOTE: this only updates full nested document
        data = data or {}
        for key, value in data.items():
            if hasattr(self, key):
                try:
                    setattr(self, key, value)
                # Calculated properties should be ignored, not set.
                except AttributeError:
                    pass

    # syntactic sugar for update (for object init)
    # Model() << {'field1': 1, 'field2': 2}
    def __lshift__(self, data):
        self.update(data)
        return self

    def clone(self):
        return self.__class__().from_dict(self.to_dict())

    def from_dict(self, data):
        raise NotImplementedError()

    def to_dict(self, keys=None):
        raise NotImplementedError()


class Event(Model):
    def __init__(
        self,
        ready_after=None,
        handler=None,
        data=None,
        group=None,
        created_at=None,
    ):
        super(Event, self).__init__()
        self.data = data
        self.group = group
        self.handler = handler
        self.ready_after = ready_after
        self.created_at = created_at

    def to_dict(self, keys=None):
        return {
            constants.Event.DATA: self.data,
            constants.Event.GROUP: self.group,
            constants.Event.HANDLER: self.handler,
            constants.Event.READY_AFTER: self.ready_after,
            constants.Event.CREATED_AT: self.created_at,
        }

    def from_dict(self, d):
        return Event(
            data=d.get(constants.Event.DATA),
            group=d.get(constants.Event.GROUP),
            handler=d.get(constants.Event.HANDLER),
            ready_after=d.get(constants.Event.READY_AFTER),
            created_at=d.get(constants.Event.CREATED_AT),
        )

    def __str__(self):
        return str(self.to_dict())
