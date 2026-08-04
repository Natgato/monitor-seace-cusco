import unittest

from seace_monitor.timeutils import iso_seace, remaining_text


class TimeUtilsTests(unittest.TestCase):
    def test_seace_date_is_converted_to_lima_iso(self):
        self.assertEqual(iso_seace("04/08/2026 16:00:00"), "2026-08-04T16:00:00-05:00")


    def test_invalid_date_is_not_invented(self):
        self.assertIsNone(iso_seace("not a date"))
        self.assertIsNone(remaining_text(None))
