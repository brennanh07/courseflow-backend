"""
Schedule Scoring Module

This module provides sophisticated schedule scoring functionality based on user preferences
and scheduling constraints. It implements advanced scoring algorithms for both time-based
and day-based schedule optimization.

Key Features:
    - Time preference scoring using exponential decay
    - Day distribution analysis and scoring
    - Preference-based schedule optimization
    - Performance optimization through caching
    - Comprehensive error handling and logging
    - Configurable scoring parameters

Example Usage:
    ```python
    preferences = {
        "preferred_time": "morning",
        "time_weight": 0.6,
        "preferred_days": ["M", "W", "F"],
        "day_weight": 0.4
    }
    
    scorer = ScheduleScorer(preferences)
    score = scorer.score_schedule(schedule_tuple)
    ```

Note:
    All scoring methods return normalized values between 0 and 1,
    where 1 represents a perfect match to preferences.
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Set, Dict, Tuple, Optional
from collections import Counter
import math
import logging
from functools import lru_cache

# Configure logging with detailed output format
logging.basicConfig(
    level=logging.DEBUG,
    filename="scheduler.log",
    filemode="w",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class TimePreference:
    """Data class to store and validate user time preferences."""

    preferred_time: str
    time_weight: float
    preferred_days: Set[str]
    day_weight: float

    def __post_init__(self):
        """Validate preferences after initialization"""
        valid_times = {"morning", "afternoon", "evening"}
        valid_days = {"M", "T", "W", "R", "F"}

        if self.preferred_time not in valid_times:
            raise ValueError(f"preferred_time must be one of {valid_times}")

        if not 0 <= self.time_weight <= 1:
            raise ValueError("time_weight must be between 0 and 1")

        if not 0 <= self.day_weight <= 1:
            raise ValueError("day_weight must be between 0 and 1")

        if not math.isclose(self.time_weight + self.day_weight, 1.0, rel_tol=1e-9):
            raise ValueError("time_weight and day_weight must sum to 1.0")

        if not self.preferred_days.issubset(valid_days):
            raise ValueError(f"preferred_days must be subset of {valid_days}")


class ScheduleScorer:
    """A schedule scoring system that evaluates schedules based on user preferences."""

    # Class-level constants
    VALID_DAYS = frozenset({"M", "T", "W", "R", "F"})

    # Define peak times for each period (not just midpoints)
    TIME_PEAKS = {
        "morning": [
            (time(8, 0), 1.0),  # 8am is ideal
            (time(9, 0), 0.9),  # 9am is nearly ideal
            (time(10, 0), 0.8),  # 10am is good
            (time(11, 0), 0.7),  # 11am is okay
            (time(12, 0), 0.6),  # 12pm is less ideal
        ],
        "afternoon": [
            (time(12, 0), 0.7),  # 12pm is good
            (time(13, 0), 0.9),  # 1pm is ideal
            (time(14, 0), 1.0),  # 2pm is ideal
            (time(15, 0), 0.9),  # 3pm is ideal
            (time(16, 0), 0.7),  # 4pm is good
        ],
        "evening": [
            (time(16, 0), 0.7),  # 4pm is good
            (time(17, 0), 0.9),  # 5pm is ideal
            (time(18, 0), 1.0),  # 6pm is ideal
            (time(19, 0), 0.9),  # 7pm is ideal
            (time(20, 0), 0.7),  # 8pm is good
        ],
    }

    # Online class scoring based on preference
    ONLINE_CLASS_SCORES = {
        "morning": 0.3,  # Online classes are less ideal for morning people
        "afternoon": 0.5,  # Neutral for afternoon preference
        "evening": 0.7,  # Better for evening preference
    }

    def __init__(self, preferences: Dict) -> None:
        """Initialize the scorer with user preferences."""
        self.preferences = TimePreference(
            preferred_time=preferences.get("preferred_time", "morning"),
            time_weight=preferences.get("time_weight", 0.5),
            preferred_days=set(preferences.get("preferred_days", [])),
            day_weight=preferences.get("day_weight", 0.5),
        )

    @staticmethod
    def _convert_to_minutes(t: time) -> int:
        """Convert time to minutes since midnight."""
        return t.hour * 60 + t.minute

    def _calculate_time_score_for_slot(self, class_time: time) -> float:
        """Calculate time score using piecewise linear interpolation between peak times."""
        if class_time == time(0, 0):  # Online class
            return self.ONLINE_CLASS_SCORES[self.preferences.preferred_time]

        peaks = self.TIME_PEAKS[self.preferences.preferred_time]
        class_minutes = self._convert_to_minutes(class_time)

        # Find surrounding peak times
        for i in range(len(peaks) - 1):
            time1, score1 = peaks[i]
            time2, score2 = peaks[i + 1]

            time1_mins = self._convert_to_minutes(time1)
            time2_mins = self._convert_to_minutes(time2)

            if time1_mins <= class_minutes <= time2_mins:
                # Linear interpolation between peaks
                ratio = (class_minutes - time1_mins) / (time2_mins - time1_mins)
                return score1 + (score2 - score1) * ratio

        # Outside preferred range - exponential falloff
        nearest_peak_mins = min(
            (abs(self._convert_to_minutes(t) - class_minutes), s) for t, s in peaks
        )[1]

        return nearest_peak_mins * 0.5  # Halve the score of nearest peak time

    @lru_cache(maxsize=1024)
    def score_schedule(self, schedule: Tuple) -> float:
        """Calculate comprehensive score for a schedule."""
        if not schedule:
            return 0.0

        try:
            time_score = self._calculate_time_score(schedule)
            day_score = self._calculate_day_score(schedule)

            return max(
                min(
                    time_score * self.preferences.time_weight
                    + day_score * self.preferences.day_weight,
                    1.0,
                ),
                0.0,
            )

        except Exception as e:
            logger.error(f"Error scoring schedule: {str(e)}")
            return 0.0

    def _calculate_time_score(self, schedule: Tuple) -> float:
        """Calculate time-based score using piecewise linear interpolation."""
        if not schedule:
            return 0.0

        scores = [
            self._calculate_time_score_for_slot(section.begin_time)
            for section in schedule
        ]

        return sum(scores) / len(scores)

    def _calculate_day_score(self, schedule: Tuple) -> float:
        """Calculate day-based score with improved distribution metrics."""
        if not schedule:
            return 0.0

        day_counts = Counter(day for section in schedule for day in section.days)

        if self.preferences.preferred_days == self.VALID_DAYS:
            return self._calculate_improved_distribution_score(day_counts)
        else:
            return self._calculate_improved_preference_score(day_counts)

    def _calculate_improved_distribution_score(self, day_counts: Counter) -> float:
        """
        Calculate distribution score with penalties for:
        1. Uneven distribution
        2. Too many consecutive days
        3. Large gaps between class days
        """
        if not day_counts:
            return 0.0

        counts = [day_counts.get(day, 0) for day in self.VALID_DAYS]

        if not any(counts):
            return 0.0

        # Base distribution score using standard deviation instead of CV
        mean = sum(counts) / len(counts)
        if mean == 0:
            return 0.0

        std_dev = math.sqrt(sum((c - mean) ** 2 for c in counts) / len(counts))
        distribution_score = 1 / (1 + std_dev)

        # Penalty for consecutive days with too many classes
        consecutive_penalty = 0.0
        for i in range(len(counts) - 1):
            if counts[i] > 0 and counts[i + 1] > 0:
                consecutive_penalty += 0.1 * min(counts[i], counts[i + 1])

        # Penalty for gaps between class days
        gap_penalty = 0.0
        last_class_day = -1
        for i, count in enumerate(counts):
            if count > 0:
                if last_class_day != -1 and i - last_class_day > 2:
                    gap_penalty += 0.1
                last_class_day = i

        return max(
            distribution_score * (1 - consecutive_penalty) * (1 - gap_penalty), 0.001
        )

    def _calculate_improved_preference_score(self, day_counts: Counter) -> float:
        """
        Calculate preference score with bonuses for:
        1. Classes on preferred days
        2. Good spacing between preferred days
        3. Reasonable class load on each day
        """
        total_classes = sum(day_counts.values())
        if total_classes == 0:
            return 0.0

        preferred_classes = sum(
            count
            for day, count in day_counts.items()
            if day in self.preferences.preferred_days
        )

        # Base score from preferred day ratio
        base_score = preferred_classes / total_classes

        # Bonus for good spacing between preferred days
        spacing_bonus = 0.0
        preferred_day_list = sorted(self.preferences.preferred_days)
        for i in range(len(preferred_day_list) - 1):
            day1, day2 = preferred_day_list[i], preferred_day_list[i + 1]
            if day_counts[day1] > 0 and day_counts[day2] > 0:
                # Bonus for MW, MF, WF patterns
                if abs(ord(day2) - ord(day1)) >= 2:
                    spacing_bonus += 0.1

        return min(base_score + spacing_bonus, 1.0)
