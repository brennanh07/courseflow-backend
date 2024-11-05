"""
Schedule Generator Module

This module provides functionality for generating optimized course schedules based on
user preferences and constraints. It uses a depth-first search algorithm combined with
a priority queue (heap) to efficiently generate and rank possible schedule combinations.

Key Features:
    - Generates multiple valid course schedules
    - Handles time conflicts and break periods
    - Scores schedules based on user preferences
    - Implements timeout mechanism for large schedule spaces
    - Memory-efficient schedule generation using heap

Example Usage:
    ```python
    # Initialize the generator
    generator = ScheduleGenerator(
        section_dict=course_sections,
        section_time_dict=section_times,
        breaks=[{"begin_time": 1200, "end_time": 1300}],
        preferences={"preferred_days": ["M", "W", "F"]},
        max_schedules=10
    )

    # Generate top schedules
    schedules = generator.generate_schedules()
    ```

Note:
    The scheduling algorithm uses a min-heap with negated scores to maintain
    the highest scoring schedules. This approach provides O(log n) insertion
    and removal operations while keeping memory usage constant.
"""

from collections import defaultdict
import heapq
from typing import List, Dict, Tuple, Any, Optional
from .schedule_scoring import ScheduleScorer
import threading
import time


class ScheduleHeapElement:
    """
    A wrapper class for schedule elements stored in the priority queue.

    This class encapsulates a schedule and its score, providing comparison
    operations necessary for heap functionality. It uses negated scores
    internally to maintain a min-heap of highest scoring schedules.

    Attributes:
        score (float): The negated score of the schedule (for min-heap operation)
        schedule (Dict[str, List[Any]]): The course schedule mapping CRNs to time slots
    """

    def __init__(self, score: float, schedule: Dict[str, List[Any]]) -> None:
        """
        Initialize a new heap element.

        Args:
            score (float): The schedule's score (will be negated internally)
            schedule (Dict[str, List[Any]]): The schedule configuration
        """
        self.score = score
        self.schedule = schedule

    def __lt__(self, other: "ScheduleHeapElement") -> bool:
        """
        Compare two elements for heap ordering.

        Args:
            other (ScheduleHeapElement): Another schedule element

        Returns:
            bool: True if this element has a lower score (higher actual score)
        """
        return self.score < other.score

    def __eq__(self, other: "ScheduleHeapElement") -> bool:
        """
        Check equality between two elements.

        Args:
            other (ScheduleHeapElement): Another schedule element

        Returns:
            bool: True if both elements have the same score
        """
        return self.score == other.score


class ScheduleGenerator:
    """
    A generator class that produces optimized course schedules.

    This class implements a depth-first search algorithm to generate valid
    course schedules while maintaining the top N schedules in a heap based
    on their scores. It handles time conflicts, break periods, and various
    scheduling constraints.

    Attributes:
        section_dict (Dict): Mapping of CRNs to section information
        section_time_dict (Dict): Mapping of CRNs to time slots
        breaks (List[Dict]): List of break periods to avoid
        preferences (Dict): User preferences for schedule optimization
        max_schedules (int): Maximum number of schedules to generate
        scorer (ScheduleScorer): Instance of scoring algorithm
        course_sections (defaultdict): Grouped sections by course
        sorted_courses (List): Courses sorted by number of sections
    """

    def __init__(
        self,
        section_dict: Dict[str, Any],
        section_time_dict: Dict[str, List[Any]],
        breaks: List[Dict[str, int]],
        preferences: Dict[str, Any],
        max_schedules: int = 20,
    ) -> None:
        """
        Initialize the schedule generator with course data and constraints.

        Args:
            section_dict: Dictionary mapping CRNs to section information
            section_time_dict: Dictionary mapping CRNs to time slots
            breaks: List of break periods with begin_time and end_time
            preferences: Dictionary of user scheduling preferences
            max_schedules: Maximum number of schedules to generate (default: 10)
        """
        # Store input parameters
        self.section_dict = section_dict
        self.section_time_dict = section_time_dict
        self.breaks = breaks
        self.preferences = preferences
        self.max_schedules = max_schedules
        self.scorer = ScheduleScorer(self.preferences)
        self.schedule_count = 0

        self.seen_scores = set()

        # Group sections by course for efficient processing
        self.course_sections = defaultdict(list)
        for crn, section in section_dict.items():
            self.course_sections[section.course].append((crn, section_time_dict[crn]))

        # Sort courses by section count to optimize search space
        self.sorted_courses = sorted(
            self.course_sections.keys(), key=lambda c: len(self.course_sections[c])
        )

    def generate_schedules(self) -> List[Tuple[float, Dict[str, List[Any]]]]:
        """
        Generate and return the top N schedules based on scoring.

        This method initiates a threaded depth-first search with a timeout
        to prevent excessive runtime on large course combinations. It returns
        schedules sorted by score in descending order.

        Returns:
            List[Tuple[float, Dict]]: List of (score, [schedule]) pairs, sorted
            by score in descending order. Returns ["timeout"] if the generation
            process exceeds the time limit.

        Note:
            The schedule generation is limited to 90 seconds to prevent
            excessive runtime in cases with many possible combinations.
        """
        heap: List[ScheduleHeapElement] = []
        self.seen_scores.clear()  # Clear seen scores for each new generation

        # Start DFS in a separate thread with timeout
        thread = threading.Thread(target=self._dfs, args=(0, {}, [], heap))
        thread.start()
        thread.join(timeout=90)  # 90-second timeout

        if thread.is_alive():
            print("Schedule generation timed out")
            return ["timeout"]

        print(f"Total schedules generated: {self.schedule_count}")

        # Convert negative scores back to positive and sort
        result = [(-element.score, element.schedule) for element in heap]
        return (sorted(result, key=lambda x: x[0], reverse=True), self.schedule_count)

    def _dfs(
        self,
        course_index: int,
        current_schedule: Dict[str, List[Any]],
        flat_schedule: List[Any],
        heap: List[ScheduleHeapElement],
    ) -> None:
        """
        Recursive depth-first search to generate valid schedules.

        This method explores possible schedule combinations while maintaining
        the top N schedules in a heap. It uses negative scores to create a
        min-heap of the highest scoring schedules.

        Args:
            course_index: Current position in sorted_courses list
            current_schedule: Mapping of CRNs to their time slots
            flat_schedule: List of all time slots in current schedule
            heap: Priority queue containing the top N schedules

        Note:
            The method modifies the heap in-place, maintaining only the
            top N schedules based on their scores.
        """
        # Base case: complete schedule found
        if course_index == len(self.sorted_courses):
            score = self.scorer.score_schedule(tuple(flat_schedule))

            # Skip if we've seen this score before
            if score in self.seen_scores:
                return

            element = ScheduleHeapElement(-score, current_schedule.copy())
            self.schedule_count += 1

            if len(heap) < self.max_schedules:
                heapq.heappush(heap, element)
                self.seen_scores.add(score)
            elif -score < heap[0].score:
                try:
                    old_score = -heap[0].score
                    self.seen_scores.remove(old_score)
                except KeyError:
                    pass  # If old score wasn't in set, that's okay
                self.seen_scores.add(score)
                heapq.heapreplace(heap, element)
            return

        # Try adding each section of the current course
        course = self.sorted_courses[course_index]
        for crn, times in self.course_sections[course]:
            if self._is_valid_addition(flat_schedule, times):
                # Create new schedule copies to prevent interference
                new_schedule = current_schedule.copy()
                new_schedule[crn] = times
                new_flat_schedule = flat_schedule + times

                # Recurse with updated schedule
                self._dfs(course_index + 1, new_schedule, new_flat_schedule, heap)

    def _is_valid_addition(
        self, current_schedule: List[Any], new_times: List[Any]
    ) -> bool:
        """
        Validate if new time slots can be added to the current schedule.

        This method checks for conflicts with existing courses and break
        periods. A conflict occurs when time slots overlap on the same days
        or when a class starts during a break period.

        Args:
            current_schedule: List of existing time slots
            new_times: List of time slots to be added

        Returns:
            bool: True if the new times can be added without conflicts
        """
        for new_time in new_times:
            # Check conflicts with existing courses
            for existing_time in current_schedule:
                if self._check_conflict(new_time, existing_time):
                    return False

            # Check conflicts with break periods
            for break_time in self.breaks:
                if (
                    new_time.begin_time >= break_time["begin_time"]
                    and new_time.begin_time <= break_time["end_time"]
                ):
                    return False
        return True

    @staticmethod
    def _check_conflict(time1: Any, time2: Any) -> bool:
        """
        Check if two time slots conflict with each other.

        A conflict occurs when two time slots share any days and their
        time ranges overlap.

        Args:
            time1: First time slot object
            time2: Second time slot object

        Returns:
            bool: True if the time slots conflict

        Note:
            Time slot objects must have 'days', 'begin_time', and 'end_time'
            attributes. Days should be comparable using set operations.
        """
        return (
            set(time1.days) & set(time2.days)  # Common days exist
            and time1.end_time > time2.begin_time  # time1 ends after time2 starts
            and time1.begin_time < time2.end_time  # time1 starts before time2 ends
        )
