from django.test import TestCase
from scheduler.constraint_schedule_generator import ConstraintBasedScheduler
from unittest.mock import patch
import datetime
from scheduler.constraint_schedule_generator import OptimizationStatus


class ConstraintBasedSchedulerTest(TestCase):
    def setUp(self):
        # Mock data for testing
        self.section_dict = {
            87086: MockSection(87086, 'MATH-1226'),
            87087: MockSection(87087, 'MATH-1226'),
            # Add more mock sections as needed
        }
        self.section_time_dict = {
            87086: [MockSectionTime('M', '10:10:00', '11:00:00')],
            87087: [MockSectionTime('W', '12:20:00', '13:10:00')],
            # Add more mock section times as needed
        }
        self.breaks = [
            {"begin_time": datetime.time(12, 0), "end_time": datetime.time(13, 0)},
            # Add more breaks as needed
        ]
        self.preferences = {
            # Add mock preferences as needed
        }

    def test_generate_time_slots(self):
        scheduler = ConstraintBasedScheduler(
            self.section_dict, self.section_time_dict, self.breaks, self.preferences
        )
        time_slots = scheduler.generate_time_slots()
        self.assertEqual(len(time_slots), 336)  # 7 days * 24 hours * 2 slots per hour

    def test_map_section_times_to_time_slots(self):
        scheduler = ConstraintBasedScheduler(
            self.section_dict, self.section_time_dict, self.breaks, self.preferences
        )
        section_time_slots = scheduler.map_section_times_to_time_slots()
        self.assertIn(87086, section_time_slots)
        self.assertIn(87087, section_time_slots)

    @patch('scheduler.constraint_schedule_generator.Model')
    def test_generate_schedules(self, MockModel):
        mock_model_instance = MockModel.return_value
        mock_model_instance.optimize.return_value = OptimizationStatus.OPTIMAL
        scheduler = ConstraintBasedScheduler(
            self.section_dict, self.section_time_dict, self.breaks, self.preferences
        )
        schedules = scheduler.generate_schedules()
        self.assertGreaterEqual(len(schedules), 1)

class MockSection:
    def __init__(self, crn, course):
        self.crn = crn
        self.course = course

class MockSectionTime:
    def __init__(self, day, begin_time, end_time):
        self.days = [day]
        self.begin_time = datetime.time.fromisoformat(begin_time)
        self.end_time = datetime.time.fromisoformat(end_time)