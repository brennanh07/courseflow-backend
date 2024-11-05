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
from typing import List, Set, Dict, Tuple, Optional, NamedTuple
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


class TimeBlock(NamedTuple):
    """Represents a time block with start and end times"""

    start: time
    end: time
    weight: float = 1.0


@dataclass
class ScoringConfig:
    """Enhanced configuration for schedule scoring"""

    time_blocks: Dict[str, List[TimeBlock]]  # Multiple weighted time blocks per period
    day_preferences: Dict[str, float]  # Weighted day preferences
    distribution_weight: float = 0.3  # Weight for distribution scoring
    preference_weight: float = 0.7  # Weight for preference matching
    time_decay_rate: float = 0.5  # Exponential decay rate
    min_score: float = 0.0001  # Minimum score threshold
    density_factor: float = 0.2  # Weight for class density scoring


class EnhancedScheduleScorer:
    """
    Enhanced schedule scoring system with improved algorithms and flexibility.
    Key improvements:
    - Multiple weighted time blocks per period
    - Class density optimization
    - Weighted day preferences
    - Improved distribution analysis
    """

    def __init__(self, preferences: Dict) -> None:
        """Initialize scorer with enhanced configuration"""
        self.config = self._create_config(preferences)
        self._setup_scoring_cache()

    def _create_config(self, preferences: Dict) -> ScoringConfig:
        """Create enhanced configuration from user preferences"""
        # Define multiple time blocks with weights for each period
        time_blocks = {
            "morning": [
                TimeBlock(time(8, 0), time(10, 0), 1.0),  # Prime morning hours
                TimeBlock(time(10, 0), time(12, 0), 0.8),  # Late morning
            ],
            "afternoon": [
                TimeBlock(time(12, 0), time(14, 0), 0.9),  # Early afternoon
                TimeBlock(time(14, 0), time(16, 0), 0.7),  # Late afternoon
            ],
            "evening": [
                TimeBlock(time(16, 0), time(18, 0), 0.8),  # Early evening
                TimeBlock(time(18, 0), time(20, 0), 0.6),  # Late evening
            ],
        }

        # Convert day preferences to weighted format
        day_preferences = {day: 1.0 for day in preferences.get("preferred_days", [])}

        return ScoringConfig(time_blocks=time_blocks, day_preferences=day_preferences)

    @lru_cache(maxsize=1024)
    def score_schedule(self, schedule: Tuple) -> float:
        """Calculate comprehensive schedule score with enhanced metrics"""
        if not schedule:
            return 0.0

        try:
            # Calculate component scores
            time_score = self._calculate_enhanced_time_score(schedule)
            day_score = self._calculate_enhanced_day_score(schedule)
            density_score = self._calculate_density_score(schedule)

            # Combine scores with weighted importance
            total_score = (
                time_score * self.config.preference_weight
                + day_score * self.config.preference_weight
                + density_score * self.config.density_factor
            )

            # Normalize final score
            return max(min(total_score, 1.0), self.config.min_score)

        except Exception as e:
            logging.error(f"Error scoring schedule: {str(e)}")
            return 0.0

    def _calculate_enhanced_time_score(self, schedule: Tuple) -> float:
        """Calculate time score using multiple weighted time blocks"""
        if not schedule:
            return 0.0

        scores = []
        for section in schedule:
            if section.begin_time == time(0, 0):  # Online/async classes
                scores.append(0.5)
                continue

            # Find best matching time block
            block_scores = []
            for blocks in self.config.time_blocks.values():
                for block in blocks:
                    if self._time_in_block(section.begin_time, block):
                        score = self._calculate_block_score(section.begin_time, block)
                        block_scores.append(score * block.weight)

            scores.append(max(block_scores) if block_scores else self.config.min_score)

        return sum(scores) / len(scores)

    def _calculate_block_score(self, class_time: time, block: TimeBlock) -> float:
        """Calculate score for a specific time block with exponential decay"""
        block_mid = self._get_block_midpoint(block)
        class_minutes = self._convert_to_minutes(class_time)
        time_diff = abs(class_minutes - block_mid)

        return math.exp(-self.config.time_decay_rate * (time_diff / 120))

    def _calculate_enhanced_day_score(self, schedule: Tuple) -> float:
        """Calculate day score with improved distribution analysis"""
        day_counts = Counter(day for section in schedule for day in section.days)

        distribution_score = self._calculate_enhanced_distribution(day_counts)
        preference_score = self._calculate_weighted_preference_score(day_counts)

        return (
            distribution_score * self.config.distribution_weight
            + preference_score * self.config.preference_weight
        )

    def _calculate_density_score(self, schedule: Tuple) -> float:
        """Calculate score based on class density per day"""
        day_counts = Counter(day for section in schedule for day in section.days)

        # Ideal density is 2-3 classes per day
        scores = []
        for count in day_counts.values():
            if count == 0:
                scores.append(0.5)  # Neutral score for empty days
            elif count <= 3:
                scores.append(1.0)  # Optimal density
            else:
                scores.append(math.exp(-(count - 3) * 0.5))  # Penalty for overcrowding

        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_enhanced_distribution(self, day_counts: Counter) -> float:
        """Calculate improved distribution score using weighted variance"""
        if not day_counts:
            return 0.0

        counts = [day_counts.get(day, 0) for day in "MTWRF"]
        if not any(counts):
            return 0.0

        mean = sum(counts) / len(counts)
        if mean == 0:
            return 0.0

        # Calculate weighted variance to account for preferred days
        weighted_variance = sum(
            (c - mean) ** 2 * self.config.day_preferences.get(day, 1.0)
            for c, day in zip(counts, "MTWRF")
        ) / len(counts)

        return 1 / (1 + math.sqrt(weighted_variance))

    def _calculate_weighted_preference_score(self, day_counts: Counter) -> float:
        """Calculate preference score with day weights"""
        total_classes = sum(day_counts.values())
        if total_classes == 0:
            return 0.0

        weighted_matches = sum(
            count * self.config.day_preferences.get(day, 0.0)
            for day, count in day_counts.items()
        )

        return max(weighted_matches / total_classes, self.config.min_score)

    # Helper methods
    def _time_in_block(self, t: time, block: TimeBlock) -> bool:
        return block.start <= t <= block.end

    def _get_block_midpoint(self, block: TimeBlock) -> int:
        start_minutes = self._convert_to_minutes(block.start)
        end_minutes = self._convert_to_minutes(block.end)
        return (start_minutes + end_minutes) // 2

    def _convert_to_minutes(self, t: time) -> int:
        return t.hour * 60 + t.minute
