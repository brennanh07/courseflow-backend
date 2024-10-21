import datetime
from collections import defaultdict
import logging
from itertools import groupby
from operator import attrgetter
from functools import lru_cache

# Setup logging
logging.basicConfig(level=logging.DEBUG, filename='scheduler.log', filemode='w')

class ScheduleScorer:
    """
    A class to score schedules based on user preferences.

    This class evaluates schedules by considering factors such as preferred days
    and times for classes.
    """

    def __init__(self, preferences):
        """
        Initialize the ScheduleScorer with user preferences.

        Args:
            preferences (dict): A dictionary containing user preferences for scheduling.
        """
        self.preferences = preferences
        self.preferred_days = tuple(preferences['preferred_days'])
        
    @lru_cache(maxsize=1024)
    def score_schedule(self, schedule):
        """
        Score a complete schedule.

        This method calculates the overall score for a schedule by summing
        the scores of individual section times.

        Args:
            schedule (tuple): A tuple of section times representing a complete schedule.

        Returns:
            float: The total score for the schedule.
        """
        return sum(self.score_section_time(section_time) for section_time in schedule)
    
    @lru_cache(maxsize=1024)
    def score_section_time(self, section_time):
        """
        Score an individual section time.

        This method calculates a score for a single section time based on
        how well it matches the user's day and time preferences.

        Args:
            section_time: An object representing a section's meeting time.

        Returns:
            float: The score for the section time.
        """
        if section_time.begin_time == datetime.time(0, 0):
            day_score = 1
            time_score = 1
        else:
            matching_days = len(set(section_time.days) & set(self.preferred_days))
            day_score = matching_days / len(section_time.days)
            time_score = self.score_time(section_time.begin_time)
        
        return (day_score * self.preferences['day_weight']) + (time_score * self.preferences['time_weight'])
    
    @lru_cache(maxsize=128)
    def score_time(self, begin_time):
        """
        Score a specific time based on how well it matches the user's preferred time range.

        Args:
            begin_time (datetime.time): The start time of a section.

        Returns:
            float: A score between 0 and 1, where 1 is a perfect match to the preferred time.
        """
        preferred_time = self.preferences['preferred_time']
        
        time_ranges = {
            'morning': (datetime.time(8, 0), datetime.time(12, 0)),
            'afternoon': (datetime.time(12, 0), datetime.time(16, 0)),
            'evening': (datetime.time(16, 0), datetime.time(20, 0)),
        }
        
        if preferred_time not in time_ranges:
            return 0
        
        preferred_start, preferred_end = time_ranges[preferred_time]
        
        if begin_time < preferred_start:
            score = max(0, 1 - (preferred_start.hour - begin_time.hour + (preferred_start.minute - begin_time.minute) / 60) / 4)
        elif preferred_start <= begin_time <= preferred_end:
            score = 1
        else:
            score = max(0, 1 - (begin_time.hour - preferred_end.hour + (begin_time.minute - preferred_end.minute) / 60) / 4)
        
        return score