import unittest
from pytz import timezone
from datetime import datetime as dt
from datetime import timedelta as delta
from reactorcore import util


class TestUtil(unittest.TestCase):

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

        for date_string, dt_object in dt_series.items():
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
        for k, v in exp1.items():
            self.assertEqual(v, act[k])

        default_dict = {'z': 6}

        exp2 = {'a': 4, 'b': 2, 'c': 3, 'd': 5, 'z': 6}

        act = util.merge_dicts(list_of_dicts, default_dict)
        for k, v in exp2.items():
            self.assertEqual(v, act[k])


    def test_safe_get(self):

        d = {'a' : 'a'}
        self.assertEqual(util.safe_get(d, 'a'), 'a')

        d = [{'a' : { 'b': 'b'}}]
        self.assertEqual(util.safe_get(d, 1), None)
        self.assertEqual(util.safe_get(d, 0, 'c'), None)
        self.assertEqual(util.safe_get(d, 0, 'a', 'b'), 'b')

