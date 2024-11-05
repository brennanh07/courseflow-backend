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


@dataclass(frozen=True)  # Made immutable for better caching
class TimePreference:
    """
    Data class to store and validate user time preferences.
    Made immutable to improve caching and prevent accidental modifications.
    """

    preferred_time: str
    time_weight: float
    preferred_days: frozenset[str]  # Changed to frozenset for immutability
    day_weight: float

    def __post_init__(self):
        # Validate weights sum to 1.0
        if not math.isclose(self.time_weight + self.day_weight, 1.0, rel_tol=1e-9):
            raise ValueError("Weights must sum to 1.0")


class ScheduleScorer:
    """A schedule scoring system that evaluates schedules based on user preferences."""

    # Class-level constants for better performance and maintenance
    VALID_TIMES = frozenset(["morning", "afternoon", "evening"])
    VALID_DAYS = frozenset(["M", "T", "W", "R", "F"])

    def __init__(self, preferences: Dict) -> None:
        """Initialize the scorer with validated user preferences."""
        # Validate preferred_time
        preferred_time = preferences.get("preferred_time", "morning")
        if preferred_time not in self.VALID_TIMES:
            raise ValueError(
                f"Invalid preferred_time. Must be one of {self.VALID_TIMES}"
            )

        # Validate and normalize weights
        time_weight = float(preferences.get("time_weight", 0.5))
        day_weight = float(preferences.get("day_weight", 0.5))

        # Validate preferred days
        raw_preferred_days = preferences.get("preferred_days", [])
        preferred_days = frozenset(
            day for day in raw_preferred_days if day in self.VALID_DAYS
        )

        self.preferences = TimePreference(
            preferred_time=preferred_time,
            time_weight=time_weight,
            preferred_days=preferred_days,
            day_weight=day_weight,
        )

        # Precompute time ranges once during initialization
        self.time_ranges = {
            "morning": (
                self._convert_to_minutes(time(8, 0)),
                self._convert_to_minutes(time(12, 0)),
            ),
            "afternoon": (
                self._convert_to_minutes(time(12, 0)),
                self._convert_to_minutes(time(16, 0)),
            ),
            "evening": (
                self._convert_to_minutes(time(16, 0)),
                self._convert_to_minutes(time(20, 0)),
            ),
        }

        # Precompute preferred time midpoint
        preferred_range = self.time_ranges[self.preferences.preferred_time]
        self.preferred_midpoint = (preferred_range[0] + preferred_range[1]) // 2

        self.TIME_DECAY_FACTOR = 0.5
        self.MIN_SCORE = 0.0001
        self.MAX_MINUTES_DIFF = 240

    @staticmethod
    @lru_cache(maxsize=1440)  # Cache full day of minute conversions
    def _convert_to_minutes(t: time) -> int:
        """Convert time to minutes since midnight with caching."""
        return t.hour * 60 + t.minute

    def _calculate_time_score(self, schedule: Tuple) -> float:
        """Calculate schedule score based on time preferences using exponential decay."""
        if not schedule:
            return 0.0

        total_score = 0
        count = 0

        for section in schedule:
            # Optimize online class handling
            if section.begin_time == time(0, 0):
                total_score += 0.5
                count += 1
                continue

            # Calculate time difference and score
            section_minutes = self._convert_to_minutes(section.begin_time)
            time_diff = abs(section_minutes - self.preferred_midpoint)

            # Use pre-calculated constants for performance
            score = math.exp(
                -self.TIME_DECAY_FACTOR * (time_diff / self.MAX_MINUTES_DIFF)
            )
            total_score += max(score, self.MIN_SCORE)
            count += 1

        return total_score / count if count > 0 else 0.0

    def _calculate_distribution_score(self, day_counts: Counter) -> float:
        """Calculate distribution evenness using optimized CV calculation."""
        if not day_counts:
            return 0.0

        # Use array operations for better performance
        counts = [day_counts.get(day, 0) for day in self.VALID_DAYS]
        total = sum(counts)

        if total == 0:
            return 0.0

        n = len(counts)
        mean = total / n

        if mean == 0:
            return 0.0

        # Optimized variance calculation
        variance = sum((c - mean) ** 2 for c in counts) / n
        cv = math.sqrt(variance) / mean

        return 1 / (1 + cv)

    def _calculate_preference_match_score(self, day_counts: Counter) -> float:
        """Calculate schedule match with preferred days using optimized counting."""
        total_classes = sum(day_counts.values())
        if total_classes == 0:
            return 0.0

        preferred_classes = sum(
            count
            for day, count in day_counts.items()
            if day in self.preferences.preferred_days
        )

        penalty = (total_classes - preferred_classes) / total_classes
        return max(1 - penalty, self.MIN_SCORE)

    def _calculate_day_score(self, schedule: Tuple) -> float:
        """Calculate schedule score based on day preferences with optimized counting."""
        if not schedule:
            return 0.0

        # Use Counter for efficient counting
        day_counts = Counter()
        for section in schedule:
            day_counts.update(section.days)

        # Choose scoring strategy based on preference coverage
        if self.preferences.preferred_days == self.VALID_DAYS:
            return self._calculate_distribution_score(day_counts)
        return self._calculate_preference_match_score(day_counts)

    @lru_cache(maxsize=1024)
    def score_schedule(self, schedule: Tuple) -> float:
        """Calculate final schedule score with improved error handling and caching."""
        if not schedule:
            return 0.0

        try:
            time_score = self._calculate_time_score(schedule)
            day_score = self._calculate_day_score(schedule)

            # Use precomputed weights for final calculation
            total_score = (
                time_score * self.preferences.time_weight
                + day_score * self.preferences.day_weight
            )

            return max(min(total_score, 1.0), 0.0)

        except Exception as e:
            logger.error(f"Error scoring schedule: {str(e)}", exc_info=True)
            return 0.0
