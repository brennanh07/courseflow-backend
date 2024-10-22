import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'class_scheduler.settings')
django.setup()

from scheduler.models import Section, SectionTime

class SectionFetcher:
    """
    A class to fetch sections and their corresponding times for given courses.
    
    This class uses Django's ORM to efficiently fetch and organize section data
    for a list of courses.
    """

    def __init__(self, courses):
        """
        Initialize the SectionFetcher with a list of courses.

        Args:
            courses (list): A list of course codes to fetch sections for.
        """
        self.courses = courses
        self.section_dict = {}
        self.section_time_dict = {}
        
    def fetch_sections(self):
        """
        Fetch all sections and their corresponding times for the given courses using batch fetching.
        
        This method uses Django's prefetch_related to optimize database queries.
        
        Returns:
            tuple: A tuple containing two dictionaries:
                - section_dict: Dictionary mapping CRNs to Section objects.
                - section_time_dict: Dictionary mapping CRNs to lists of SectionTime objects.
        """
        # logger.info(f"Fetching sections for courses: {self.courses}")
        
        # Fetch sections with related SectionTime objects in a single query
        sections = Section.objects.filter(course__in=self.courses).prefetch_related('sectiontime_set')
        # logger.debug(f"Found {len(sections)} sections")
        
        # Organize fetched data into dictionaries for easy access
        self.section_dict = {section.crn: section for section in sections}
        self.section_time_dict = {section.crn: list(section.sectiontime_set.all()) for section in sections}
        
        # logger.debug(f"Fetched sections: {self.section_dict}")
        # logger.debug(f"Fetched section times: {self.section_time_dict}")
        
        if not self.section_dict:
            pass
            # logger.warning(f"No sections found for courses: {self.courses}")
        
        return self.section_dict, self.section_time_dict