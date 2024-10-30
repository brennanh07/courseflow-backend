"""
VT Course Section Scraper

This module implements a Scrapy spider for scraping course section data from Virginia Tech's course timetable.
It handles both open sections and all sections (open/closed), storing the data in a MySQL database.

The spider crawls VT's Banner system, extracts course information including CRNs, schedules, professors,
and other metadata, then calculates and stores grade distributions.

Requirements:
    - scrapy
    - django
    - MySQLdb
    - python-environ
    - logging

Environment Variables Required:
    - DB_HOST: Database host address
    - DB_USER: Database username
    - DB_PASSWORD: Database password
    - DB_NAME: Database name
"""

import scrapy
from scrapy.http import FormRequest
import os
import django
import MySQLdb
import environ
from datetime import datetime
import logging
from django.db import transaction
from scheduler.models import Section, GradeDistribution, SectionOpenOrClosed
from django.db.models import Avg
from decimal import Decimal, ROUND_HALF_UP

# Configure logging
logger = logging.getLogger(__name__)

env = environ.Env()
env_path = os.path.join(os.path.dirname(__file__), ".env")
environ.Env.read_env(env_path)

# Setup Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "class_scheduler.settings")
django.setup()


class SectionsSpider(scrapy.Spider):
    """
    Spider for scraping course section data from Virginia Tech's Banner system.

    This spider handles both open sections and all sections (open/closed), maintaining
    separate data structures for each. It processes various course formats including
    regular sections, online asynchronous courses, and arranged meetings.

    Attributes:
        name (str): Spider identifier used by Scrapy
        allowed_domains (list): Domains the spider is allowed to crawl
        start_urls (list): Initial URL to begin the crawl
        current_crn (int): Currently processing Course Reference Number
        sections_data (list): Storage for open sections data
        section_times_data (list): Storage for open sections' time data
        sections_data_open_or_closed (list): Storage for all sections data
        section_times_data_open_or_closed (list): Storage for all sections' time data
    """

    name = "sections"
    allowed_domains = ["apps.es.vt.edu", "selfservice.banner.vt.edu"]
    start_urls = ["https://selfservice.banner.vt.edu/ssb/HZSKVTSC.P_ProcRequest"]

    def __init__(self, *args, **kwargs):
        """
        Initialize the spider with database connection and data storage.

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Raises:
            MySQLdb.Error: If database connection fails
        """
        super(SectionsSpider, self).__init__(*args, **kwargs)
        self.current_crn = None
        logger.info("Initializing SectionsSpider")
        try:
            # Establish database connection using environment variables
            self.conn = MySQLdb.connect(
                host=env("DB_HOST"),
                user=env("DB_USER"),
                passwd=env("DB_PASSWORD"),
                db=env("DB_NAME"),
            )
            self.cursor = self.conn.cursor()
            logger.info("Successfully connected to database")
        except MySQLdb.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
        # Initialize data storage lists
        self.sections_data = []
        self.section_times_data = []
        self.sections_data_open_or_closed = []
        self.section_times_data_open_or_closed = []

    def start_requests(self):
        """
        Initialize the crawl by preparing tables for updates.
        Returns:
            Iterator[FormRequest]: Requests for each subject, both open-only and all sections
        """
        logger.info("Preparing tables for updates")
        try:
            # Execute each CREATE TABLE statement separately
            statements = [
                "DROP TEMPORARY TABLE IF EXISTS temp_section",
                "DROP TEMPORARY TABLE IF EXISTS temp_sectiontime",
                "DROP TEMPORARY TABLE IF EXISTS temp_sectionopenorclosed",
                "DROP TEMPORARY TABLE IF EXISTS temp_sectiontimeopenorclosed",
                "CREATE TEMPORARY TABLE temp_section LIKE scheduler_section",
                "CREATE TEMPORARY TABLE temp_sectiontime LIKE scheduler_sectiontime",
                "CREATE TEMPORARY TABLE temp_sectionopenorclosed LIKE scheduler_sectionopenorclosed",
                "CREATE TEMPORARY TABLE temp_sectiontimeopenorclosed LIKE scheduler_sectiontimeopenorclosed"
            ]
            
            for statement in statements:
                self.cursor.execute(statement)
                # Fetch any results (even if there are none) to clear the connection
                self.cursor.fetchall()
            
            self.conn.commit()
            logger.info("Successfully created temporary tables")

            # Get subjects using a new cursor to avoid mixing queries
            with self.conn.cursor() as subjects_cursor:
                subjects_cursor.execute("SELECT abbreviation FROM scheduler_subject")
                subjects = [row[0] for row in subjects_cursor.fetchall()]
                
            logger.info(f"Retrieved {len(subjects)} subjects to process")
            
            return self.make_requests(subjects)

        except MySQLdb.Error as e:
            logger.error(f"Database error in start_requests: {e}")
            raise

    def get_subjects(self):
        """
        Retrieve list of subject abbreviations from the database.

        Returns:
            list: Subject abbreviations (e.g., ['CS', 'MATH', 'PHYS'])

        Raises:
            MySQLdb.Error: If database query fails
        """
        try:
            self.cursor.execute("SELECT abbreviation FROM scheduler_subject")
            subjects = [row[0] for row in self.cursor.fetchall()]
            return subjects
        except MySQLdb.Error as e:
            logger.error(f"Failed to retrieve subjects: {e}")
            raise

    def make_requests(self, subjects):
        """
        Generate FormRequests for each subject, both for open-only and all sections.

        Args:
            subjects (list): List of subject abbreviations to process

        Returns:
            Iterator[FormRequest]: Form requests for each subject and section type
        """
        for subject in subjects:
            # Generate request for open sections
            yield FormRequest(
                url=self.start_urls[0],
                formdata={
                    "CAMPUS": "0",
                    "TERMYEAR": "202501",  # Spring 2025
                    "CORE_CODE": "AR%",
                    "subj_code": subject,
                    "SCHDTYPE": "%",
                    "CRSE_NUMBER": "",
                    "crn": "",
                    "open_only": "on",
                    "sess_code": "%",
                    "BTN_PRESSED": "FIND class sections",
                    "disp_comments_in": "N",
                },
                callback=self.parse,
                meta={"subject": subject, "open_only": True},
            )

            # Generate request for all sections
            yield FormRequest(
                url=self.start_urls[0],
                formdata={
                    "CAMPUS": "0",
                    "TERMYEAR": "202501",
                    "CORE_CODE": "AR%",
                    "subj_code": subject,
                    "SCHDTYPE": "%",
                    "CRSE_NUMBER": "",
                    "crn": "",
                    "open_only": "",
                    "sess_code": "%",
                    "BTN_PRESSED": "FIND class sections",
                    "disp_comments_in": "N",
                },
                callback=self.parse,
                meta={"subject": subject, "open_only": False},
            )

    def parse(self, response):
        """
        Parse the response from Banner for course sections.

        Handles different types of course formats:
        - Regular sections (13 columns)
        - Arranged sections (12 columns)
        - Online asynchronous sections (12 columns)
        - Additional time slots (9-10 columns)

        Args:
            response (scrapy.http.Response): Response from Banner system
        """
        subject = response.meta["subject"]
        open_only = response.meta["open_only"]

        # Process each row in the course table
        rows = response.xpath("//table[@class='dataentrytable']/tr[position()>1]")

        for row in rows:
            cells = row.xpath(".//td")
            # Route to appropriate parser based on cell count and content
            if len(cells) == 10 or len(cells) == 9:
                self.parse_additional_time(cells, open_only)
            elif (
                len(cells) == 12
                and cells[4].xpath(".//text()").get().strip() == "Online: Asynchronous"
            ):
                self.parse_online_asynchronous(cells, open_only)
            elif len(cells) == 13:
                self.parse_regular(cells, open_only)
            elif len(cells) == 12:
                self.parse_arranged(cells, open_only)
            else:
                logger.warning(
                    f"Skipping row with unexpected number of cells: {len(cells)}"
                )
                continue

    def parse_additional_time(self, cells, open_only):
        """
        Parse additional time slots for a course section.

        Args:
            cells (list): Cell data from the table row
            open_only (bool): Whether processing open sections only
        """
        if len(cells) == 10:
            days_string = cells[5].xpath(".//text()").get().strip()
            begin_time = self.convert_time(cells[6].xpath(".//text()").get().strip())
            end_time = self.convert_time(cells[7].xpath(".//text()").get().strip())
        else:
            # Handle arranged times with default values
            days_string = "ARR"
            begin_time = "00:00:00"
            end_time = "00:00:00"

        self.add_section_times(
            self.current_crn, days_string, begin_time, end_time, open_only
        )

    def parse_regular(self, cells, open_only):
        """
        Parse regular course sections with standard meeting times.

        Args:
            cells (list): Cell data from the table row
            open_only (bool): Whether processing open sections only
        """
        # Extract CRN and basic course information
        self.current_crn = int(cells[0].xpath(".//b/text()").get().strip())

        course = cells[1].xpath(".//font/text()").get().strip()
        credit_hours = cells[5].xpath(".//text()").get().strip()
        class_type = cells[3].xpath(".//text()").get().strip()

        # Append 'B' to course code for 0-credit labs
        if credit_hours == "0" and class_type == "B":
            course += "B"

        # Compile section data
        section_data = (
            self.current_crn,
            course,
            cells[2].xpath(".//text()").get().strip(),
            class_type,
            cells[4].xpath(".//text()").get().strip(),
            credit_hours,
            cells[6].xpath(".//text()").get().strip(),
            cells[7].xpath(".//text()").get().strip(),
            cells[11].xpath(".//text()").get().strip(),
            cells[12].xpath(".//a/text()").get().strip(),
            None,  # placeholder for avg_gpa
        )

        # Store section data in appropriate list
        if open_only:
            self.sections_data.append(section_data)
        else:
            self.sections_data_open_or_closed.append(section_data)

        # Process meeting times
        days_string = cells[8].xpath(".//text()").get().strip()
        begin_time = self.convert_time(cells[9].xpath(".//text()").get().strip())
        end_time = self.convert_time(cells[10].xpath(".//text()").get().strip())

        self.add_section_times(
            self.current_crn, days_string, begin_time, end_time, open_only
        )

    def parse_online_asynchronous(self, cells, open_only):
        """
        Parse online asynchronous course sections.

        Args:
            cells (list): Cell data from the table row
            open_only (bool): Whether processing open sections only
        """
        # Similar structure to parse_regular but with different cell indices
        self.current_crn = int(cells[0].xpath(".//b/text()").get().strip())

        course = cells[1].xpath(".//font/text()").get().strip()
        credit_hours = cells[5].xpath(".//text()").get().strip()
        class_type = cells[3].xpath(".//text()").get().strip()

        if credit_hours == "0" and class_type == "B":
            course += "B"

        section_data = (
            self.current_crn,
            course,
            cells[2].xpath(".//text()").get().strip(),
            class_type,
            cells[4].xpath(".//text()").get().strip(),
            credit_hours,
            cells[6].xpath(".//text()").get().strip(),
            cells[7].xpath(".//text()").get().strip(),
            cells[10].xpath(".//text()").get().strip(),
            cells[11].xpath(".//a/text()").get().strip(),
            None,
        )

        if open_only:
            self.sections_data.append(section_data)
        else:
            self.sections_data_open_or_closed.append(section_data)

        # Use default time values for online courses
        days_string = "ONLINE"
        begin_time = "00:00:00"
        end_time = "00:00:00"

        self.add_section_times(
            self.current_crn, days_string, begin_time, end_time, open_only
        )

    def parse_arranged(self, cells, open_only):
        """
        Parse arranged course sections (no fixed meeting times).

        Args:
            cells (list): Cell data from the table row
            open_only (bool): Whether processing open sections only
        """
        # Similar structure to other parse methods but with arranged time handling
        self.current_crn = int(cells[0].xpath(".//b/text()").get().strip())

        course = cells[1].xpath(".//font/text()").get().strip()
        credit_hours = cells[5].xpath(".//text()").get().strip()
        class_type = cells[3].xpath(".//text()").get().strip()

        if credit_hours == "0" and class_type == "B":
            course += "B"

        section_data = (
            self.current_crn,
            course,
            cells[2].xpath(".//text()").get().strip(),
            class_type,
            cells[4].xpath(".//text()").get().strip(),
            credit_hours,
            cells[6].xpath(".//text()").get().strip(),
            cells[7].xpath(".//text()").get().strip(),
            cells[10].xpath(".//text()").get().strip(),
            cells[11].xpath(".//a/text()").get().strip(),
            None,
        )

        if open_only:
            self.sections_data.append(section_data)
        else:
            self.sections_data_open_or_closed.append(section_data)

        # Use default values for arranged courses
        days_string = "ARR"
        begin_time = "00:00:00"
        end_time = "00:00:00"

        self.add_section_times(
            self.current_crn, days_string, begin_time, end_time, open_only
        )

    def add_section_times(self, crn, days, begin_time, end_time, open_only):
        """
        Helper function to add section time information to appropriate data structure.

        Args:
            crn (str): Course Reference Number
            days (str): Days of the week for the section
            begin_time (str): Start time in HH:MM:SS format
            end_time (str): End time in HH:MM:SS format
            open_only (bool): Whether processing open sections only
        """
        # Split days string into individual days and store each separately
        days_split = days.split()
        for day in days_split:
            section_time_data = (crn, day, begin_time, end_time)
            if open_only:
                self.section_times_data.append(section_time_data)
            else:
                self.section_times_data_open_or_closed.append(section_time_data)

    def convert_time(self, time_str):
        """
        Convert time from 12-hour format to 24-hour format.

        Args:
            time_str (str): Time in 12-hour format (e.g., "9:05AM")

        Returns:
            str: Time in 24-hour format (HH:MM:SS)

        Raises:
            ValueError: If time string is in invalid format
        """
        try:
            return datetime.strptime(time_str, "%I:%M%p").strftime("%H:%M:%S")
        except ValueError as e:
            logger.error(f"Failed to convert time {time_str}: {e}")
            raise

    def update_section_gpas(self):
        """
        Update GPA values for both open sections and all sections tables.

        This method calculates and updates the average GPA for each section based on
        historical grade distribution data. It processes both open sections and
        all sections (open/closed) separately.

        Note:
            - GPA calculations are based on matching professor's last name
            - Results are rounded to two decimal places
        """
        logger.info("Starting GPA update for all section tables...")

        # Update GPAs for open sections
        self._update_gpas_for_table(Section, "open sections")

        # Update GPAs for all sections (open and closed)
        self._update_gpas_for_table(SectionOpenOrClosed, "all sections")

    def _update_gpas_for_table(self, model_class, table_description):
        """
        Helper method to update GPAs for a specific section model.

        Args:
            model_class (django.db.models.Model): Django model class (Section or SectionOpenOrClosed)
            table_description (str): Description of the table for logging purposes

        Note:
            This method uses database transactions to ensure data consistency
            and handles exceptions for each section independently.
        """
        updated_count = 0
        not_found_count = 0

        try:
            with transaction.atomic():
                # Process each section in the model
                for section in model_class.objects.all():
                    try:
                        # Extract professor's last name for matching
                        professor_last_name = section.professor.split()[-1]

                        # Find matching grade distributions
                        matching_distributions = GradeDistribution.objects.filter(
                            full_course=section.course,
                            professor__icontains=professor_last_name,
                        )

                        if matching_distributions.exists():
                            # Calculate and round average GPA
                            avg_gpa = matching_distributions.aggregate(Avg("gpa"))[
                                "gpa__avg"
                            ]
                            rounded_gpa = Decimal(str(avg_gpa)).quantize(
                                Decimal("0.01"), rounding=ROUND_HALF_UP
                            )
                            section.avg_gpa = rounded_gpa
                            section.save()
                            updated_count += 1
                        else:
                            not_found_count += 1

                    except Exception as e:
                        logger.error(
                            f"Error processing {table_description} section {section.crn}: {str(e)}"
                        )

            logger.info(
                f"GPA update complete for {table_description} - Updated: {updated_count}, Not found: {not_found_count}"
            )
        except Exception as e:
            logger.error(
                f"Error during GPA update transaction for {table_description}: {str(e)}"
            )

    def close(self, reason):
        """
        Update existing records and insert new ones when spider closes.
        """
        logger.info(f"Spider closing. Reason: {reason}")

        try:
            # Insert data into temporary tables
            logger.info("Inserting data into temporary tables")

            # Insert open sections data
            self.cursor.executemany(
                "INSERT INTO temp_section (crn, course, title, class_type, modality, credit_hours, capacity, professor, location, exam_code, avg_gpa) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                self.sections_data,
            )
            self.conn.commit()

            self.cursor.executemany(
                "INSERT INTO temp_sectiontime (crn_id, days, begin_time, end_time) VALUES (%s, %s, %s, %s)",
                self.section_times_data,
            )
            self.conn.commit()

            # Insert all sections data
            self.cursor.executemany(
                "INSERT INTO temp_sectionopenorclosed (crn, course, title, class_type, modality, credit_hours, capacity, professor, location, exam_code, avg_gpa) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                self.sections_data_open_or_closed,
            )
            self.conn.commit()

            self.cursor.executemany(
                "INSERT INTO temp_sectiontimeopenorclosed (crn_id, days, begin_time, end_time) VALUES (%s, %s, %s, %s)",
                self.section_times_data_open_or_closed,
            )
            self.conn.commit()

            # Update existing records and insert new ones
            logger.info("Updating existing records and inserting new ones")

            # Update open sections - Execute each statement separately
            update_statements = [
                """
                UPDATE scheduler_section s
                JOIN temp_section ts ON s.crn = ts.crn
                SET 
                    s.course = ts.course,
                    s.title = ts.title,
                    s.class_type = ts.class_type,
                    s.modality = ts.modality,
                    s.credit_hours = ts.credit_hours,
                    s.capacity = ts.capacity,
                    s.professor = ts.professor,
                    s.location = ts.location,
                    s.exam_code = ts.exam_code
                """,
                """
                INSERT INTO scheduler_section
                SELECT ts.* FROM temp_section ts
                LEFT JOIN scheduler_section s ON ts.crn = s.crn
                WHERE s.crn IS NULL
                """,
                """
                DELETE st FROM scheduler_sectiontime st
                LEFT JOIN temp_sectiontime tst ON st.crn_id = tst.crn_id AND st.days = tst.days
                WHERE tst.crn_id IS NULL
                """,
                """
                INSERT INTO scheduler_sectiontime
                SELECT tst.* FROM temp_sectiontime tst
                LEFT JOIN scheduler_sectiontime st 
                ON tst.crn_id = st.crn_id AND tst.days = st.days
                WHERE st.id IS NULL
                """,
                """
                UPDATE scheduler_sectionopenorclosed s
                JOIN temp_sectionopenorclosed ts ON s.crn = ts.crn
                SET 
                    s.course = ts.course,
                    s.title = ts.title,
                    s.class_type = ts.class_type,
                    s.modality = ts.modality,
                    s.credit_hours = ts.credit_hours,
                    s.capacity = ts.capacity,
                    s.professor = ts.professor,
                    s.location = ts.location,
                    s.exam_code = ts.exam_code
                """,
                """
                INSERT INTO scheduler_sectionopenorclosed
                SELECT ts.* FROM temp_sectionopenorclosed ts
                LEFT JOIN scheduler_sectionopenorclosed s ON ts.crn = s.crn
                WHERE s.crn IS NULL
                """,
                """
                DELETE st FROM scheduler_sectiontimeopenorclosed st
                LEFT JOIN temp_sectiontimeopenorclosed tst 
                ON st.crn_id = tst.crn_id AND st.days = tst.days
                WHERE tst.crn_id IS NULL
                """,
                """
                INSERT INTO scheduler_sectiontimeopenorclosed
                SELECT tst.* FROM temp_sectiontimeopenorclosed tst
                LEFT JOIN scheduler_sectiontimeopenorclosed st 
                ON tst.crn_id = st.crn_id AND st.days = st.days
                WHERE st.id IS NULL
                """
            ]

            # Execute each statement separately and commit
            for statement in update_statements:
                self.cursor.execute(statement)
                self.conn.commit()

            logger.info("Successfully updated database")

            # Update GPAs for all sections
            self.update_section_gpas()

        except Exception as e:
            logger.error(f"Database error during update: {e}")
            self.conn.rollback()
            print("An error occurred:", e)

        finally:
            # Drop temporary tables and close connections
            try:
                # Execute each DROP statement separately
                drop_statements = [
                    "DROP TEMPORARY TABLE IF EXISTS temp_section",
                    "DROP TEMPORARY TABLE IF EXISTS temp_sectiontime",
                    "DROP TEMPORARY TABLE IF EXISTS temp_sectionopenorclosed",
                    "DROP TEMPORARY TABLE IF EXISTS temp_sectiontimeopenorclosed"
                ]
                
                for statement in drop_statements:
                    self.cursor.execute(statement)
                    self.conn.commit()
                    
            except Exception as e:
                logger.error(f"Error dropping temporary tables: {e}")

            logger.info("Closing database connections")
            self.cursor.close()
            self.conn.close()
