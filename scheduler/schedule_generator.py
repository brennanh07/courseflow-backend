from collections import defaultdict
import heapq
from typing import List, Dict, Tuple, Any
from schedule_scoring import ScheduleScorer
import threading
import time


class ScheduleHeapElement:
    """
    A class to represent elements in the schedule heap.

    This class is used to store schedules along with their scores in a heap,
    allowing for efficient retrieval of the top-scoring schedules.
    """

    def __init__(self, score: float, schedule: Dict[str, List[Any]]):
        """
        Initialize a ScheduleHeapElement.

        Args:
            score (float): The score of the schedule.
            schedule (Dict[str, List[Any]]): The schedule represented as a dictionary.
        """
        self.score = score
        self.schedule = schedule

    def __lt__(self, other):
        """
        Compare two ScheduleHeapElements based on their scores.

        This method is implemented to allow the heap to be a max-heap.

        Args:
            other (ScheduleHeapElement): The other element to compare with.

        Returns:
            bool: True if this element's score is greater than the other's, False otherwise.
        """
        return self.score > other.score

    def __eq__(self, other):
        """
        Check if two ScheduleHeapElements are equal based on their scores.

        Args:
            other (ScheduleHeapElement): The other element to compare with.

        Returns:
            bool: True if the scores are equal, False otherwise.
        """
        return self.score == other.score 


class ScheduleGenerator:
    """
    A class to generate valid course schedules based on given constraints and preferences.

    This class uses a depth-first search algorithm to generate schedules and a heap
    to maintain the top-scoring schedules.
    """

    def __init__(
        self, section_dict, section_time_dict, breaks, preferences, max_schedules=10
    ):
        """
        Initialize the ScheduleGenerator.

        Args:
            section_dict (Dict): Dictionary of sections keyed by CRN.
            section_time_dict (Dict): Dictionary of section times keyed by CRN.
            breaks (List): List of break times to avoid scheduling classes.
            preferences (Dict): User preferences for scheduling.
            max_schedules (int, optional): Maximum number of schedules to generate. Defaults to 10.
        """
        self.section_dict = section_dict
        self.section_time_dict = section_time_dict
        self.breaks = breaks
        self.preferences = preferences
        self.max_schedules = max_schedules
        self.scorer = ScheduleScorer(self.preferences)

        # Group section times by course for efficient processing
        self.course_sections = defaultdict(list)
        for crn, section in section_dict.items():
            self.course_sections[section.course].append((crn, section_time_dict[crn]))

        # Sort courses by the number of sections (ascending) to optimize search
        self.sorted_courses = sorted(
            self.course_sections.keys(), key=lambda c: len(self.course_sections[c])
        )

    def generate_schedules(self):
        """
        Generate and return the top schedules based on user preferences.

        This method starts a thread to perform the depth-first search and waits for
        a maximum of 90 seconds before timing out.

        Returns:
            List[Tuple[float, Dict]]: A list of tuples containing schedule scores and schedules.
        """
        heap = []
        thread = threading.Thread(target=self._dfs, args=(0, {}, [], heap))
        thread.start()
        thread.join(timeout=90)  # Timeout after 1 minute 30 seconds
        if thread.is_alive():
            print("Schedule generation timed out")
            return ["timeout"]

        return [
            (element.score, element.schedule) for element in sorted(heap)
        ]

    def _dfs(
        self,
        course_index: int,
        current_schedule: Dict[str, List[Any]],
        flat_schedule: List[Any],
        heap: List[ScheduleHeapElement],
    ):
        """
        Perform a depth-first search to generate valid schedules.

        This recursive method builds schedules by adding sections for each course,
        checking for conflicts, and updating the heap of top schedules.

        Args:
            course_index (int): The index of the current course being processed.
            current_schedule (Dict[str, List[Any]]): The current partial schedule.
            flat_schedule (List[Any]): A flat list of all section times in the current schedule.
            heap (List[ScheduleHeapElement]): The heap of top schedules.
        """
        if course_index == len(self.sorted_courses):
            # Complete schedule found, score it and update the heap
            score = self.scorer.score_schedule(tuple(flat_schedule))
            element = ScheduleHeapElement(score, current_schedule.copy())
            if len(heap) < self.max_schedules:
                heapq.heappush(heap, element)
            elif score > heap[0].score:
                heapq.heapreplace(heap, element)
            return

        course = self.sorted_courses[course_index]
        for crn, times in self.course_sections[course]:
            if self._is_valid_addition(flat_schedule, times):
                # Add the section to the schedule and continue the search
                current_schedule[crn] = times
                self._dfs(
                    course_index + 1, current_schedule, flat_schedule + times, heap
                )
                current_schedule.pop(crn)

    def _is_valid_addition(
        self, current_schedule: List[Any], new_times: List[Any]
    ) -> bool:
        """
        Check if adding new section times to the current schedule is valid.

        This method checks for conflicts with existing times and breaks.

        Args:
            current_schedule (List[Any]): The current list of scheduled times.
            new_times (List[Any]): The new times to be added.

        Returns:
            bool: True if the addition is valid, False otherwise.
        """
        for new_time in new_times:
            # Check for conflicts with existing times
            for existing_time in current_schedule:
                if self._check_conflict(new_time, existing_time):
                    return False

            # Check for conflicts with breaks
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

        Args:
            time1 (Any): The first time slot.
            time2 (Any): The second time slot.

        Returns:
            bool: True if there is a conflict, False otherwise.
        """
        return (
            set(time1.days) & set(time2.days)
            and time1.end_time > time2.begin_time
            and time1.begin_time < time2.end_time
        )