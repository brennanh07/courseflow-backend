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
    """
    Data class to store and validate user time preferences.
    """

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
    """
    A schedule scoring system that evaluates schedules based on user preferences.
    """

    # Class-level constants
    VALID_DAYS = frozenset({"M", "T", "W", "R", "F"})
    TIME_RANGES = {
        "morning": (time(8, 0), time(12, 0)),
        "afternoon": (time(12, 0), time(16, 0)),
        "evening": (time(16, 0), time(20, 0)),
    }
    TIME_DECAY_FACTOR = 0.5
    MIN_SCORE = 0.0001
    MAX_MINUTES_DIFF = 240
    ONLINE_CLASS_NEUTRAL_SCORE = 0.5

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

    @classmethod
    def _get_preferred_midpoint(cls, preferred_time: str) -> Optional[int]:
        """Calculate the midpoint of a preferred time range in minutes."""
        time_range = cls.TIME_RANGES.get(preferred_time)
        if not time_range:
            return None

        start_minutes = cls._convert_to_minutes(time_range[0])
        end_minutes = cls._convert_to_minutes(time_range[1])
        return start_minutes + (end_minutes - start_minutes) // 2

    def _calculate_section_time_score(
        self, section_time: time, preferred_mid: int
    ) -> float:
        """Calculate time score for a single section."""
        if section_time == time(0, 0):
            return self.ONLINE_CLASS_NEUTRAL_SCORE

        section_minutes = self._convert_to_minutes(section_time)
        time_diff = abs(section_minutes - preferred_mid)
        normalized_diff = time_diff / self.MAX_MINUTES_DIFF

        return max(math.exp(-self.TIME_DECAY_FACTOR * normalized_diff), self.MIN_SCORE)

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
        """Calculate time-based score using exponential decay."""
        if not schedule:
            return 0.0

        preferred_mid = self._get_preferred_midpoint(self.preferences.preferred_time)
        if preferred_mid is None:
            return 0.0

        scores = [
            self._calculate_section_time_score(section.begin_time, preferred_mid)
            for section in schedule
        ]

        return sum(scores) / len(scores)

    def _calculate_day_score(self, schedule: Tuple) -> float:
        """Calculate day-based score considering preferences and distribution."""
        if not schedule:
            return 0.0

        day_counts = Counter(day for section in schedule for day in section.days)

        return (
            self._calculate_distribution_score(day_counts)
            if self.preferences.preferred_days == self.VALID_DAYS
            else self._calculate_preference_match_score(day_counts)
        )

    def _calculate_distribution_score(self, day_counts: Counter) -> float:
        """Calculate evenness of class distribution using coefficient of variation."""
        if not day_counts:
            return 0.0

        counts = [day_counts.get(day, 0) for day in self.VALID_DAYS]

        if not any(counts):
            return 0.0

        mean = sum(counts) / len(counts)
        if mean == 0:
            return 0.0

        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        cv = math.sqrt(variance) / mean

        return max(1 / (1 + cv), self.MIN_SCORE)

    def _calculate_preference_match_score(self, day_counts: Counter) -> float:
        """Calculate score based on matching preferred days."""
        total_classes = sum(day_counts.values())
        if total_classes == 0:
            return 0.0

        preferred_classes = sum(
            count
            for day, count in day_counts.items()
            if day in self.preferences.preferred_days
        )

        return max(preferred_classes / total_classes, self.MIN_SCORE)
