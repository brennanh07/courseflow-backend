import scrapy
from scrapy.http import FormRequest
import os
import django
import MySQLdb
import environ
from datetime import datetime
import logging
from django.db import transaction
from scheduler.models import Section, GradeDistribution
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

# print("DB_NAME:", env("DB_NAME"))
# print("DB_USER:", env("DB_USER"))
# print("DB_PASSWORD:", env("DB_PASSWORD"))
# print("DB_HOST:", env("DB_HOST"))


class SectionsSpider(scrapy.Spider):
    name = "sections"
    allowed_domains = ["apps.es.vt.edu", "selfservice.banner.vt.edu"]
    start_urls = ["https://selfservice.banner.vt.edu/ssb/HZSKVTSC.P_ProcRequest"]

    def __init__(self, *args, **kwargs):
        super(SectionsSpider, self).__init__(*args, **kwargs)
        self.current_crn = None
        logger.info("Initializing SectionsSpider")
        try:
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
        self.sections_data = []
        self.section_times_data = []

    def start_requests(self):
        # Clear tables
        logger.info("Clearing existing data from tables")
        try:
            self.cursor.execute("DELETE FROM scheduler_sectiontime")
            self.cursor.execute("DELETE FROM scheduler_section")
            self.cursor.execute("ALTER TABLE scheduler_sectiontime AUTO_INCREMENT = 1")
            self.conn.commit()
            logger.info("Successfully cleared tables")
        except MySQLdb.Error as e:
            logger.error(f"Failed to clear tables: {e}")
            raise

        subjects = self.get_subjects()
        logger.info(f"Retrieved {len(subjects)} subjects to process")
        return self.make_requests(subjects)

    def get_subjects(self):
        try:
            self.cursor.execute("SELECT abbreviation FROM scheduler_subject")
            subjects = [row[0] for row in self.cursor.fetchall()]
            # logger.debug(f"Retrieved subjects: {subjects}")
            return subjects
        except MySQLdb.Error as e:
            logger.error(f"Failed to retrieve subjects: {e}")
            raise

    def make_requests(self, subjects):
        for subject in subjects:
            # logger.info(f"Making request for subject: {subject}")
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
                    "open_only": "on",
                    "sess_code": "%",
                    "BTN_PRESSED": "FIND class sections",
                    "disp_comments_in": "N",
                },
                callback=self.parse,
                meta={"subject": subject},
            )

    def parse(self, response):
        subject = response.meta["subject"]
        # logger.info(f"Parsing response for subject: {subject}")
        
        # log raw html response
        # subject = response.meta["subject"]
        # filename = f"sections_{subject}.html"
        # with open (filename, 'w', encoding='utf-8') as f:
        #     f.write(response.text)

        rows = response.xpath("//table[@class='dataentrytable']/tr[position()>1]")
        # logger.info(f"Found {len(rows)} rows to process for subject {subject}")
        
        for row in rows:
            cells = row.xpath(".//td")
            if len(cells) == 10 or len(cells) == 9:
                # logger.debug("Processing additional time row")
                self.parse_additional_time(cells)
            elif (
                len(cells) == 12
                and cells[4].xpath(".//text()").get().strip() == "Online: Asynchronous"
            ):
                # logger.debug("Processing online asynchronous row")
                self.parse_online_asynchronous(cells)
            elif len(cells) == 13:
                # logger.debug("Processing regular row")
                self.parse_regular(cells)
            elif len(cells) == 12:
                # logger.debug("Processing arranged row")
                self.parse_arranged(cells)
            else:
                logger.warning(f"Skipping row with unexpected number of cells: {len(cells)}")
                continue

    def parse_additional_time(self, cells):
        # logger.debug(f"Parsing additional time for CRN: {self.current_crn}")
        if len(cells) == 10:
            days_string = cells[5].xpath(".//text()").get().strip()
            begin_time = self.convert_time(cells[6].xpath(".//text()").get().strip())
            end_time = self.convert_time(cells[7].xpath(".//text()").get().strip())
        else:
            days_string = "ARR"
            begin_time = "00:00:00"
            end_time = "00:00:00"

        self.add_section_times(self.current_crn, days_string, begin_time, end_time)

    def parse_regular(self, cells):
        self.current_crn = int(cells[0].xpath(".//b/text()").get().strip())
        # logger.info(f"Parsing regular section with CRN: {self.current_crn}")

        course = cells[1].xpath(".//font/text()").get().strip()
        credit_hours = cells[5].xpath(".//text()").get().strip()
        class_type = cells[3].xpath(".//text()").get().strip()

        # If course is lab, add "B" to end of course code
        if credit_hours == "0" and class_type == "B":
            course += "B"
            # logger.debug(f"Added 'B' suffix to lab course: {course}")

        section_data = (
            self.current_crn,  # Extract CRN from <b> tag
            course,  # Extract Course from <font> tag
            cells[2].xpath(".//text()").get().strip(),  # title
            class_type,  # class type
            cells[4].xpath(".//text()").get().strip(),  # modality
            credit_hours,  # credit hours
            cells[6].xpath(".//text()").get().strip(),  # capacity
            cells[7].xpath(".//text()").get().strip(),  # professor
            cells[11].xpath(".//text()").get().strip(),  # location
            cells[12].xpath(".//a/text()").get().strip(),  # exam code
            None,
        )

        self.sections_data.append(section_data)
        # logger.debug(f"Added section data for CRN {self.current_crn}")

        days_string = cells[8].xpath(".//text()").get().strip()
        begin_time = self.convert_time(cells[9].xpath(".//text()").get().strip())
        end_time = self.convert_time(cells[10].xpath(".//text()").get().strip())

        self.add_section_times(self.current_crn, days_string, begin_time, end_time)

    def parse_online_asynchronous(self, cells):
        self.current_crn = int(cells[0].xpath(".//b/text()").get().strip())
        # logger.info(f"Parsing online asynchronous section with CRN: {self.current_crn}")

        course = cells[1].xpath(".//font/text()").get().strip()
        credit_hours = cells[5].xpath(".//text()").get().strip()
        class_type = cells[3].xpath(".//text()").get().strip()

        # If course is lab, add "B" to end of course code
        if credit_hours == "0" and class_type == "B":
            course += "B"
            # logger.debug(f"Added 'B' suffix to lab course: {course}")

        section_data = (
            self.current_crn,
            course,  # course
            cells[2].xpath(".//text()").get().strip(),  # title
            class_type,  # class type
            cells[4].xpath(".//text()").get().strip(),  # modality
            credit_hours,  # credit hours
            cells[6].xpath(".//text()").get().strip(),  # capacity
            cells[7].xpath(".//text()").get().strip(),  # professor
            cells[10].xpath(".//text()").get().strip(),  # location
            cells[11].xpath(".//a/text()").get().strip(),  # exam code
            None,
        )

        self.sections_data.append(section_data)
        # logger.debug(f"Added online asynchronous section data for CRN {self.current_crn}")

        days_string = "ONLINE"
        begin_time = "00:00:00"
        end_time = "00:00:00"

        self.add_section_times(self.current_crn, days_string, begin_time, end_time)

    def parse_arranged(self, cells):
        self.current_crn = int(cells[0].xpath(".//b/text()").get().strip())
        # logger.info(f"Parsing arranged section with CRN: {self.current_crn}")

        course = cells[1].xpath(".//font/text()").get().strip()
        credit_hours = cells[5].xpath(".//text()").get().strip()
        class_type = cells[3].xpath(".//text()").get().strip()

        # If course is lab, add "B" to end of course code
        if credit_hours == "0" and class_type == "B":
            course += "B"
            # logger.debug(f"Added 'B' suffix to lab course: {course}")

        section_data = (
            self.current_crn,
            course,  # course
            cells[2].xpath(".//text()").get().strip(),  # title
            class_type,  # class type
            cells[4].xpath(".//text()").get().strip(),  # modality
            credit_hours,  # credit hours
            cells[6].xpath(".//text()").get().strip(),  # capacity
            cells[7].xpath(".//text()").get().strip(),  # professor
            cells[10].xpath(".//text()").get().strip(),  # location
            cells[11].xpath(".//a/text()").get().strip(),  # exam code
            None,
        )

        self.sections_data.append(section_data)
        # logger.debug(f"Added arranged section data for CRN {self.current_crn}")

        days_string = "ARR"
        begin_time = "00:00:00"
        end_time = "00:00:00"

        self.add_section_times(self.current_crn, days_string, begin_time, end_time)

    def add_section_times(self, crn, days, begin_time, end_time):
        # logger.debug(f"Adding section times for CRN {crn}: days={days}, begin={begin_time}, end={end_time}")
        days_split = days.split()
        for day in days_split:
            section_time_data = (crn, day, begin_time, end_time)
            self.section_times_data.append(section_time_data)

    def convert_time(self, time_str):
        try:
            return datetime.strptime(time_str, "%I:%M%p").strftime("%H:%M:%S")
        except ValueError as e:
            logger.error(f"Failed to convert time {time_str}: {e}")
            raise
        
    def update_section_gpas(self):
        """Update GPA values for all sections based on matching GradeDistribution records."""
        logger.info("Starting GPA update for sections...")
        updated_count = 0
        not_found_count = 0

        try:
            with transaction.atomic():
                # Process all sections
                for section in Section.objects.all():
                    try:
                        # Extract last name from professor field
                        professor_last_name = section.professor.split()[-1]
                        # print(professor_last_name)
                        
                        # Try to find matching grade distributions
                        matching_distributions = GradeDistribution.objects.filter(
                            full_course=section.course,
                            professor__icontains=professor_last_name
                        )

                        if matching_distributions.exists():
                            # Calculate average GPA across all matching distributions
                            avg_gpa = matching_distributions.aggregate(Avg('gpa'))['gpa__avg']
                            rounded_gpa = Decimal(str(avg_gpa)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) 
                            section.avg_gpa = rounded_gpa
                            section.save()
                            updated_count += 1
                            # logger.debug(f"Updated section {section.crn} with averaged GPA {avg_gpa} from {matching_distributions.count()} distributions")
                        else:
                            not_found_count += 1
                            # logger.warning(f"No GPA data found for section {section.crn}: {section.course} with professor last name {professor_last_name}")

                    except Exception as e:
                        logger.error(f"Error processing section {section.crn}: {str(e)}")

            logger.info(f"GPA update complete - Updated: {updated_count}, Not found: {not_found_count}")
        except Exception as e:
            logger.error(f"Error during GPA update transaction: {str(e)}")

    def close(self, reason):
        logger.info(f"Spider closing. Reason: {reason}")
        # print("Inserting into scheduler_section:")
        # print("SQL:", "INSERT INTO scheduler_section (crn, course, title, class_type, modality, credit_hours, capacity, professor, location, exam_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
        # print("Data:", self.sections_data)

        # print("Inserting into scheduler_sectiontime:")
        # print("SQL:", "INSERT INTO scheduler_sectiontime (crn, days, begin_time, end_time) VALUES (%s, %s, %s, %s)")
        # print("Data:", self.section_times_data)

        try:
            logger.info(f"Inserting {len(self.sections_data)} sections into database")
            self.cursor.executemany(
                "INSERT INTO scheduler_section (crn, course, title, class_type, modality, credit_hours, capacity, professor, location, exam_code, avg_gpa) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                self.sections_data,
            )
            
            logger.info(f"Inserting {len(self.section_times_data)} section times into database")
            self.cursor.executemany(
                "INSERT INTO scheduler_sectiontime (crn_id, days, begin_time, end_time) VALUES (%s, %s, %s, %s)",
                self.section_times_data,
            )
            self.conn.commit()
            logger.info("Successfully committed all data to database")
            
            self.update_section_gpas()
            
        except Exception as e:
            logger.error(f"Database error during final insert: {e}")
            print("An error occurred:", e)

        finally:
            logger.info("Closing database connections")
            self.cursor.close()
            self.conn.close()