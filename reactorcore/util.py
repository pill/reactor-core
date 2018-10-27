import sys
import traceback
import csv

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import codecs
from datetime import datetime, date
import itertools
import os
import json
import delorean
import functools
import logging
import random
import re
import string
from unicodedata import normalize

# import bleach
from tornado import gen
from tornado.ioloop import IOLoop

from reactorcore import exception

PUNCT_RE = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
ZIP_RE = re.compile("^\d{5}(?:[-\s]\d{4})?$")

logger = logging.getLogger(__name__)


class AttributeDict(dict):
    """A dictionary-like object allowing indexed and attribute access."""

    def __init__(self, *args, **kwargs):
        super(AttributeDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class DateTimeEncoder(json.JSONEncoder):
    """This is needed because it can handle the
    `indent` argument, and `datetime_handler` does not
    """

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, "to_dict"):
            # it's probably a model
            return "{} id:{}".format(str(obj), obj.id)
        return super(DateTimeEncoder, self).default(obj)


# ***********************************************************************
# TEXT/HTML
# ***********************************************************************


def shorten_text(text, max_len=400, show_more_text=""):
    """
    Shorten a body of text.
        text - the string to be shortened, or self if not long enough
        max_len - maximum length in characters of text body
        show_more_text - the string that will be attached to end of text IF trim
    """
    if text == None:
        return None

    cutoff_string = "... "

    shorter = None
    if len(text) > max_len + len(cutoff_string):
        shorter = text[:max_len] + cutoff_string + show_more_text

    return shorter or text


def slugify(text, delim="-"):
    """Generates a ASCII-only slug."""
    text = unicode(text)
    result = []
    for word in PUNCT_RE.split(text.lower()):
        word = normalize("NFKD", word).encode("ascii", "ignore")
        if word:
            result.append(word)
    return unicode(delim.join(result))


def gen_random_string(size=10, chars=string.ascii_letters + string.digits):
    return "".join(random.choice(chars) for x in range(size))


# def linkify_text(text):
#     """
#     Use bleach library to sanitize and linkify links in input
#     as html links. Include shortening
#     """
#     return bleach.linkify(text, callbacks=[_shorten_url])


# def strip_embed_size_tags(html):
#     strainer = SoupStrainer(['iframe', 'img'])
#     soup = BeautifulSoup(html, 'lxml',  parse_only=strainer)
#     for tag in soup():
#         for attribute in ["height", "width"]:
#             del tag[attribute]

#     # fix
#     soup = str(soup).replace('allowfullscreen=""', 'allowfullscreen')
#     return soup


# ***********************************************************************
# CSV/UTF-8
# ***********************************************************************


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """

    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ***********************************************************************
# DECORATORS
# ***********************************************************************


def calculate_cache_key(key, *args, **kwargs):
    # is it a function? then just call the function
    if callable(key):
        # make sure the cache key calculation function doesnt bail out
        try:
            cache_key = key(args, kwargs)
        except Exception as ex:
            logger.error("Error calculating cache key: %s", ex)
            return None

    # ... else, just use the supplied key
    else:
        cache_key = key
    return cache_key


# memoize decorator of caching, key OR function
def set_cache(key, expire=None):
    """Decorator to memoize functions.
      Args:

      key: The key to use for the cache. The key can either be a
           function os a string. A function will be called with *args
           and **kwargs that were passed to the function being decorated
    """

    def decorator(fxn):
        @gen.coroutine
        def wrapper(*args, **kwargs):
            import application

            cache = application.get_application().service.cache

            # is it a function? then just call the function
            cache_key = calculate_cache_key(key, *args, **kwargs)
            if not cache_key:
                yield fxn(*args, **kwargs)

            data = yield cache.get(cache_key)
            if data is not None:
                raise gen.Return(data)

            # if not found in cache, call the wrapped function
            data = yield fxn(*args, **kwargs)

            # then save the results
            yield cache.set(cache_key, data, expire=expire)
            raise gen.Return(data)

        return wrapper

    return decorator


# flush cache for a key
def flush_cache(key):
    def decorator(fxn):
        @gen.coroutine
        def wrapper(*args, **kwargs):
            import application

            cache = application.get_application().service.cache

            # is it a function? then just call the function
            cache_key = calculate_cache_key(key, *args, **kwargs)
            yield cache.flush(pattern=cache_key)

            # now call the wrapped function
            res = yield fxn(*args, **kwargs)
            raise gen.Return(res)

        return wrapper

    return decorator


# Jobs - coroutines that block and run within a separate
# new worker process
def job(f):
    @functools.wraps(f)
    @gen.coroutine
    def decorated_function(*args, **kwargs):
        import application

        jobs = application.get_application().service.jobs

        partial_f = functools.partial(f, *args, **kwargs)

        # If asynchronous, this code will run in a separate worker process.
        # Create a new IO loop and run it.
        if jobs.is_async():
            try:
                IOLoop.instance().run_sync(partial_f)
            except exception.NotFound:
                ex_type, ex, last_tb = sys.exc_info()
                tb = traceback.extract_tb(last_tb)
                file_name, line, func, failed_code = tb[-1]
                logger.error(
                    'Error: %s. Occurred at: %s:%s %s() in "%s"',
                    ex.message,
                    file_name,
                    line,
                    func,
                    failed_code,
                    exc_info=True,
                )
            except exception.DuplicateError:
                ex_type, ex, last_tb = sys.exc_info()
                tb = traceback.extract_tb(last_tb)
                file_name, line, func, failed_code = tb[-1]
                logger.error(
                    'Error: %s. Occurred at: %s:%s %s() in "%s"',
                    ex.message,
                    file_name,
                    line,
                    func,
                    failed_code,
                    exc_info=True,
                )
            except UnicodeEncodeError:
                ex_type, ex, last_tb = sys.exc_info()
                tb = traceback.extract_tb(last_tb)
                file_name, line, func, failed_code = tb[-1]
                logger.error(
                    'Error: %s. Occurred at: %s:%s %s() in "%s"',
                    ex.message,
                    file_name,
                    line,
                    func,
                    failed_code,
                    exc_info=True,
                )
            except Exception:
                ex_type, ex, last_tb = sys.exc_info()
                tb = traceback.extract_tb(last_tb)
                file_name, line, func, failed_code = tb[-1]
                logger.critical(
                    '[EXCEPTION] Error: %s. Occurred at: %s:%s %s() in "%s"',
                    ex.message,
                    file_name,
                    line,
                    func,
                    failed_code,
                    exc_info=True,
                )
        else:
            # already within IOLoop - just yield the future
            yield partial_f()

        raise gen.Return(None)

    return decorated_function


def coroutine_partial(func, *args, **keywords):
    """Yields and raises as you would for coroutine and bakes
    the extra args and kwargs like a partial"""

    @gen.coroutine
    def newfunc(*fargs, **fkeywords):
        # we want pass by referencewhere
        # newkeywords = keywords.copy()
        newkeywords = keywords
        newkeywords.update(fkeywords)
        res = yield func(*(args + fargs), **newkeywords)
        raise gen.Return(res)

    newfunc.func = func
    newfunc.args = args
    newfunc.keywords = keywords
    # return a Future to yield
    return newfunc


# ***********************************************************************
# MISC
# ***********************************************************************


def utc_time():
    return datetime.utcnow()


def local_time():
    return datetime.now()


# Return only certain parts of a dictionary
# If no keys are given, the original dictionary is returned
def select(d, keys):
    if not keys:
        return d
    return {k: v for k, v in d.items() if k in keys}


def unselect(d, keys):
    if not keys:
        return d
    return {k: v for k, v in d.items() if k not in keys}


def zip_check(query_str):
    """
    Check if query_str is a zipcode.
    """
    return re.match(ZIP_RE, query_str)


# converter for date/time for JSON operations
datetime_handler = lambda obj: (
    obj.isoformat() if isinstance(obj, (datetime, date)) else None
)


def prettify_time(event_time, now=None):
    """
    For a given item/comment/reply date-time, returns a string
    representing the relative time to the user.
    e.g.
    """

    # TODO: fix me
    if isinstance(event_time, unicode):
        try:
            event_time = datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%S.%f")
        except:
            return str(event_time)

    if not event_time:
        return None

    now = now or utc_time()
    delta = int((now - event_time).total_seconds())

    if delta < 60:
        return "Just now"
    elif delta < 60 * 60:
        return "%dm ago" % (delta / 60)
    elif delta < 60 * 60 * 24:
        return "%dh ago" % (delta / 3600)
    else:
        return event_time.strftime("%B %d, %Y").replace(" 0", " ")


def str_to_dt(date_str):
    """
    Convert timestamp date_str passed forward from front-end as
    datetime object.
    """

    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str

    return delorean.parse(date_str).datetime

    # def sanitize_html_input(text):
    #     """
    #     Use bleach library to sanitize html text.
    #     This mitigates the risk of scripting attacks.
    #     """
    #     # Clean JS attacks.
    #     bleached_text = bleach.clean(text, tags=[], attributes=[], styles=[], strip=True)

    # Remove excess newlines.
    return re.sub("\n\n+", "\n\n", bleached_text)


def _shorten_url(attrs, new=False):
    """
    Callback to be used in bleach's linkify.

    Shortens overly-long URLs in the text.
    """
    if not new:  # Only looking at newly-created links.
        return attrs

    # _text will be the same as the URL for new links.
    text = attrs["_text"]
    if len(text) > 25:
        attrs["_text"] = text[0:22] + "..."
    attrs["target"] = "_blank"
    return attrs


def prepend_dict_key(orig, prep_text, camel_case=False):
    """
    Return a new dictionary for which every key is prepended with prep_text.
    """
    if camel_case:
        return dict(
            (prep_text + str(k).title(), v) for k, v in orig.items()
        )
    else:
        return dict((prep_text + str(k), v) for k, v in orig.items())


def pluck(dct, *keys):
    """
    Returns a tuple of the values for each key from the dict, None for missing key.
    """
    return (dct.get(key) for key in keys)


def merge_dicts(dict_list, default_dict=None):
    """
    Creates a new dict representing the merger of all dicts in dict_list.
    If default_dict is given, add keys to default_dict.
    """
    if not default_dict:
        return reduce(lambda a, b: a.update(b) or a, dict_list)
    else:
        for d in dict_list:
            default_dict.update(d)
        return default_dict


def group_and_create_lookup(things, key_func):
    """
    Takes list of things then sorts, groups, and
    returns a lookup with result of `key_func`
    as the key and list of things grouped on key
    as the value
    """
    things = things or []
    things = sorted(things, key=key_func)
    return {k: list(g) for k, g in itertools.groupby(things, key_func)}


def json_print(dict_data):
    print(json.dumps(dict_data, cls=DateTimeEncoder, indent=2))


def safe_get(dct, *key_path):
    """
    Return value if all keys exist (in order)
    else return None
    """
    for k in key_path:

        if isinstance(k, int) and k < len(dct):
            dct = dct[k]
        elif k in dct:
            dct = dct[k]
        else:
            logger.warn(
                "Key not found in dict: %s %s", str(dct), str(key_path)
            )
            return None
    return dct


def deep_get(d, path):
    # safe return deep path (dot separated) in dict
    # otherwise return None
    cur = d
    for p in path.split("."):
        cur = cur.get(p)
        if not cur:
            return None
    return cur
