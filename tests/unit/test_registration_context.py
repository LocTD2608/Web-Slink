import unittest
from src.backend.core.domain.entities.time_slot import TimeSlot


class ExactScheduleTests(unittest.TestCase):
    def test_sunday_last_periods(self):
        self.assertEqual(TimeSlot(8, 10, 12).period_indices(), [81, 82, 83])

    def test_invalid_periods_rejected(self):
        for values in [(9, 1, 3), (2, 0, 1), (2, 4, 3)]:
            with self.assertRaises(ValueError):
                TimeSlot(*values).period_indices()
