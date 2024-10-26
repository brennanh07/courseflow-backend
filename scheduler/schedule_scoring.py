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

    Attributes:
        preferred_time (str): Desired time of day ('morning', 'afternoon', 'evening')
        time_weight (float): Weight factor for time-based scoring (0-1)
        preferred_days (Set[str]): Set of preferred days (M, T, W, R, F)
        day_weight (float): Weight factor for day-based scoring (0-1)

    Note:
        time_weight and day_weight should sum to 1.0 for proper score normalization
    """

    preferred_time: str
    time_weight: float
    preferred_days: Set[str]
    day_weight: float


class ScheduleScorer:
    """
    A sophisticated schedule scoring system that evaluates schedules based on
    user preferences and optimal distribution patterns.

    This class implements multiple scoring algorithms including:
        - Exponential decay for time preference matching
        - Distribution analysis for day scheduling
        - Weighted scoring combining multiple factors
        - Performance-optimized calculations

    Attributes:
        preferences (TimePreference): User's scheduling preferences
        time_ranges (Dict): Defined time periods for different parts of day
        TIME_DECAY_FACTOR (float): Controls exponential decay rate in time scoring
        MIN_SCORE (float): Minimum score threshold
        MAX_MINUTES_DIFF (int): Maximum time difference to consider
    """

    def __init__(self, preferences: Dict) -> None:
        """
        Initialize the scorer with user preferences and scoring parameters.

        Args:
            preferences (Dict): Dictionary containing:
                - preferred_time (str): Desired time of day
                - time_weight (float): Weight for time scoring
                - preferred_days (List[str]): Preferred days of week
                - day_weight (float): Weight for day scoring

        Note:
            Default values are provided for missing preferences to ensure
            robust initialization.
        """
        # Convert raw preferences to structured TimePreference object
        self.preferences = TimePreference(
            preferred_time=preferences.get("preferred_time", "morning"),
            time_weight=preferences.get("time_weight", 0.5),
            preferred_days=set(preferences.get("preferred_days", [])),
            day_weight=preferences.get("day_weight", 0.5),
        )

        # Define standard time ranges for different periods
        self.time_ranges = {
            "morning": (time(8, 0), time(12, 0)),
            "afternoon": (time(12, 0), time(16, 0)),
            "evening": (time(16, 0), time(20, 0)),
        }

        # Scoring algorithm constants
        self.TIME_DECAY_FACTOR = 0.5  # Controls score decay rate
        self.MIN_SCORE = 0.0001  # Prevents negative/zero scores
        self.MAX_MINUTES_DIFF = 240  # Maximum time difference to consider

    def _convert_to_minutes(self, t: time) -> int:
        """
        Convert a time object to minutes since midnight for easier calculations.

        Args:
            t (time): Time object to convert

        Returns:
            int: Number of minutes since midnight

        Example:
            >>> _convert_to_minutes(time(14, 30))
            870  # (14 * 60 + 30)
        """
        return t.hour * 60 + t.minute

    @lru_cache(maxsize=1024)
    def score_schedule(self, schedule: Tuple) -> float:
        """
        Calculate a comprehensive score for a complete schedule.

        This method combines time-based and day-based scores using the specified
        weights. The scoring process is cached for performance optimization.

        Args:
            schedule (Tuple): Tuple of course sections with their times

        Returns:
            float: Normalized score between 0 and 1

        Raises:
            Exception: Logs any scoring errors and returns 0.0

        Note:
            The score is cached using @lru_cache for performance optimization
            when scoring multiple similar schedules.
        """
        if not schedule:
            return 0.0

        try:
            # Calculate component scores
            time_score = self._calculate_time_score(schedule)
            day_score = self._calculate_day_score(schedule)

            # Combine scores using weighted average
            total_score = (
                time_score * self.preferences.time_weight
                + day_score * self.preferences.day_weight
            )

            # Ensure score is properly normalized
            return max(min(total_score, 1.0), 0.0)

        except Exception as e:
            logger.error(f"Error scoring schedule: {str(e)}")
            return 0.0

    def _calculate_time_score(self, schedule: Tuple) -> float:
        """
        Calculate schedule score based on time preferences using exponential decay.

        The score decreases exponentially as class times deviate from the
        preferred time period. Online/async classes receive a neutral score.

        Args:
            schedule (Tuple): Tuple of course sections

        Returns:
            float: Time-based score between 0 and 1

        Note:
            Uses exponential decay function: score = e^(-decay_factor * normalized_diff)
        """
        if not schedule:
            return 0.0

        # Get preferred time range midpoint
        preferred_range = self.time_ranges.get(self.preferences.preferred_time)
        if not preferred_range:
            return 0.0

        # Calculate middle of preferred time range
        preferred_mid = (
            self._convert_to_minutes(preferred_range[0])
            + (
                self._convert_to_minutes(preferred_range[1])
                - self._convert_to_minutes(preferred_range[0])
            )
            / 2
        )

        scores = []
        for section in schedule:
            # Handle online/async classes
            if section.begin_time == time(0, 0):
                scores.append(0.5)
                continue

            # Calculate time difference and score
            section_minutes = self._convert_to_minutes(section.begin_time)
            time_diff = abs(section_minutes - preferred_mid)

            # Apply exponential decay function
            score = math.exp(
                -self.TIME_DECAY_FACTOR * (time_diff / self.MAX_MINUTES_DIFF)
            )
            scores.append(max(score, self.MIN_SCORE))

        return sum(scores) / len(scores)

    def _calculate_day_score(self, schedule: Tuple) -> float:
        """
        Calculate schedule score based on day preferences and distribution.

        This method uses different scoring strategies depending on whether
        all days are preferred or specific days are preferred.

        Args:
            schedule (Tuple): Tuple of course sections

        Returns:
            float: Day-based score between 0 and 1

        Note:
            For all days preferred: Rewards even distribution
            For specific days: Rewards matching preferred days
        """
        if not schedule:
            return 0.0

        # Count classes per day
        day_counts = Counter()
        for section in schedule:
            for day in section.days:
                day_counts[day] += 1

        # Choose scoring strategy based on preferences
        if self.preferences.preferred_days == set(["M", "T", "W", "R", "F"]):
            return self._calculate_distribution_score(day_counts)
        else:
            return self._calculate_preference_match_score(day_counts)

    def _calculate_distribution_score(self, day_counts: Counter) -> float:
        """
        Calculate how evenly classes are distributed across the week.

        Uses coefficient of variation (CV) to measure distribution evenness.
        A lower CV indicates more even distribution.

        Args:
            day_counts (Counter): Number of classes per day

        Returns:
            float: Distribution evenness score between 0 and 1

        Note:
            Score = 1 / (1 + CV) where CV is the coefficient of variation
        """
        if not day_counts:
            return 0.0

        # Get counts for all weekdays
        all_days = set(["M", "T", "W", "R", "F"])
        counts = [day_counts.get(day, 0) for day in all_days]

        if not any(counts):
            return 0.0

        # Calculate coefficient of variation
        mean = sum(counts) / len(counts)
        if mean == 0:
            return 0.0

        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean

        # Convert CV to score
        return 1 / (1 + cv)

    def _calculate_preference_match_score(self, day_counts: Counter) -> float:
        """
        Calculate how well the schedule matches preferred days.

        Penalizes classes scheduled on non-preferred days by reducing
        the score proportionally to the number of such classes.

        Args:
            day_counts (Counter): Number of classes per day

        Returns:
            float: Preference match score between 0 and 1

        Note:
            Score = 1 - (non_preferred_classes / total_classes)
        """
        total_classes = sum(day_counts.values())
        if total_classes == 0:
            return 0.0

        # Count classes on preferred days
        preferred_day_classes = sum(
            count
            for day, count in day_counts.items()
            if day in self.preferences.preferred_days
        )

        # Calculate penalty for non-preferred days
        non_preferred_day_classes = total_classes - preferred_day_classes
        penalty = non_preferred_day_classes / total_classes

        return max(1 - penalty, self.MIN_SCORE)
