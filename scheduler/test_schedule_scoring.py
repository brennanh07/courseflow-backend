import unittest
from unittest.mock import MagicMock
from schedule_scoring import ScheduleScorer
import datetime

class TestScheduleScorer(unittest.TestCase):
    
    def setUp(self):
        # Sample user preferences
        self.preferences = {
            'preferred_days': ['M', 'T', 'W', 'R', 'F'],
            'preferred_time': 'morning',
            'day_weight': 0.5,
            'time_weight': 0.5
        }
        self.scorer = ScheduleScorer(self.preferences)

    def test_score_time_morning(self):
        """Test score_time with a time within the morning range."""
        begin_time = datetime.time(9, 0)  # 9:00 AM
        score = self.scorer.score_time(begin_time, 'morning')
        self.assertEqual(score, 1)

    def test_score_time_outside_range(self):
        """Test score_time with a time outside the preferred range."""
        begin_time = datetime.time(13, 0)  # 1:00 PM
        score = self.scorer.score_time(begin_time, 'morning')
        self.assertLess(score, 1)
        self.assertGreater(score, 0)

    def test_score_time_before_morning(self):
        """Test score_time with a time before the morning range."""
        begin_time = datetime.time(7, 0)  # 7:00 AM
        score = self.scorer.score_time(begin_time, 'morning')
        self.assertEqual(score, 0)

    def test_score_time_after_evening(self):
        """Test score_time with a time after the evening range."""
        begin_time = datetime.time(21, 0)  # 9:00 PM
        score = self.scorer.score_time(begin_time, 'evening')
        self.assertEqual(score, 0)

    def test_score_section_time(self):
        """Test score_section_time for a section time object."""
        section_time = MagicMock(begin_time=datetime.time(9, 0), days='MWF')
        score = self.scorer.score_section_time(section_time)
        self.assertGreater(score, 0)  # Score should be positive

    def test_score_section_time_online(self):
        """Test score_section_time for an online section (begin_time '00:00:00')."""
        section_time = MagicMock(begin_time=datetime.time(0, 0), days='N/A')
        score = self.scorer.score_section_time(section_time)
        self.assertEqual(score, 1)  # Online classes should score perfectly

    def test_score_section(self):
        """Test score_section to ensure correct average score calculation."""
        section_times = [
            MagicMock(begin_time=datetime.time(9, 0), days='M'),
            MagicMock(begin_time=datetime.time(10, 0), days='MWF')
        ]
        section = MagicMock()
        score = self.scorer.score_section(section, section_times)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 1)

    def test_score_schedule(self):
        """Test score_schedule for a complete schedule."""
        section_times = [
            MagicMock(begin_time=datetime.time(9, 0), days='MWF', crn=1),
            MagicMock(begin_time=datetime.time(10, 0), days='MWF', crn=2)
        ]
        schedule = section_times
        score = self.scorer.score_schedule(schedule)
        self.assertGreater(score, 0)  # Ensure the schedule has a positive score

    def test_group_section_times_by_section(self):
        """Test that group_section_times_by_section correctly groups SectionTime objects."""
        section_time1 = MagicMock(crn=1, begin_time=datetime.time(9, 0), days='MWF')
        section_time2 = MagicMock(crn=1, begin_time=datetime.time(10, 0), days='MWF')
        section_time3 = MagicMock(crn=2, begin_time=datetime.time(9, 0), days='TR')

        section_times = [section_time1, section_time2, section_time3]
        grouped = self.scorer.group_section_times_by_section(section_times)

        self.assertIn(1, grouped)
        self.assertIn(2, grouped)
        self.assertEqual(len(grouped[1]), 2)
        self.assertEqual(len(grouped[2]), 1)

if __name__ == '__main__':
    unittest.main()