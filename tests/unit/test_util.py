import unittest
from pytz import timezone
from datetime import datetime as dt
from datetime import timedelta as delta
from reactorcore import util


class TestUtil(unittest.TestCase):

    def test_prettify_time(self):
        """
        Return string corresponding to relative time between now and
        0-59 seconds => "Just now"
        1-59 minutes => "[# of minutes]m ago"
        1-24 hours => "[# of hours]h ago"
        24 hours + => "[Month] [dd], [year]"
        """
        begin = dt(2015, 1, 1, 0, 0, 0)
        date_series = {
            "Just now": (begin, begin + delta(seconds=59.99999)),
            "1m ago": (begin, begin + delta(seconds=60)),
            "59m ago": (begin, begin + delta(seconds=60 * 59.99999)),
            "1h ago": (begin, begin + delta(seconds=60 * 60)),
            "23h ago": (begin, begin + delta(seconds=60 * 60 * 23.99999)),
            "January 1, 2015": (begin, begin + delta(days=2)),
            "January 2, 2015": (begin + delta(days=1), None),
            "February 3, 2015": (dt(2015, 2, 3, 18, 6, 46), None)
            # no @now passed in, defaults month format.
        }

        for exp, date_tuple in date_series.iteritems():
            s, e = date_tuple
            self.assertEqual(exp, util.prettify_time(s, now=e))

    def test_str_to_dt(self):
        """
        Convert date string to datetime obj. Handle ms correctly
        """

        tz = timezone('UTC')

        dt_series = {
            dt(2015, 4, 2, 16, 23, 22, 875): dt(2015, 4, 2, 16, 23, 22, 875),
            '2015-04-02T16:23:22.875000': dt(
                2015, 4, 2, 16, 23, 22, 875000, tzinfo=tz),
            '2015-04-02T16:23:22.875': dt(
                2015, 4, 2, 16, 23, 22, 875000, tzinfo=tz),
            '2015-04-02T16:23:22': dt(
                2015, 4, 2, 16, 23, 22, tzinfo=tz),
            '2015-04-02T16:23:22Z': dt(
                2015, 4, 2, 16, 23, 22, tzinfo=tz)
        }

        for date_string, dt_object in dt_series.iteritems():
            self.assertEqual(dt_object, util.str_to_dt(date_string))

    def test_shorten_text(self):
        from loremipsum import get_sentences
        too_short = 'test'
        shortened = util.shorten_text(too_short, max_len=100)
        self.assertEquals(too_short, shortened)

        same = 'test'
        shortened = util.shorten_text(too_short, max_len=len(same))
        self.assertEquals(too_short, shortened)

        longer = ''
        while len(longer) < 100:
            longer = longer + ' ' + get_sentences(1)[0]
        longer = longer + get_sentences(1)[0]

        shortened = util.shorten_text(longer, max_len=100)
        self.assertTrue(len(shortened) < len(longer))

        about_same = 'test 1'
        shortened = util.shorten_text(about_same, max_len=5)
        self.assertEquals(about_same, shortened)

    def test_pluck(self):
        things = {'blah': 'bleh', 'foo': 'bar'}
        foo, blah = util.pluck(things, 'foo', 'blah')

        self.assertEqual(foo, 'bar')
        self.assertEqual(blah, 'bleh')

        other = {'blah': 'bleh', 'foo': 'bar'}
        _, not_there = util.pluck(other, 'foo', 'not_there')
        self.assertEqual(not_there, None)

    def test_merge_dicts(self):
        list_of_dicts = [
            {'a': 1},
            {'b': 2, 'c': 3},
            {'a': 4, 'd': 5}]

        exp1 = {'a': 4, 'b': 2, 'c': 3, 'd': 5}

        act = util.merge_dicts(list_of_dicts)
        for k, v in exp1.iteritems():
            self.assertEqual(v, act[k])

        default_dict = {'z': 6}

        exp2 = {'a': 4, 'b': 2, 'c': 3, 'd': 5, 'z': 6}

        act = util.merge_dicts(list_of_dicts, default_dict)
        for k, v in exp2.iteritems():
            self.assertEqual(v, act[k])


    def test_safe_get(self):

        d = {'a' : 'a'}
        self.assertEqual(util.safe_get(d, 'a'), 'a')

        d = [{'a' : { 'b': 'b'}}]
        self.assertEqual(util.safe_get(d, 1), None)
        self.assertEqual(util.safe_get(d, 0, 'c'), None)
        self.assertEqual(util.safe_get(d, 0, 'a', 'b'), 'b')

