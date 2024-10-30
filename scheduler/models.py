from django.db import models


class Subject(models.Model):
    abbreviation = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    
    def __str__(self):
        return (f"{self.abbreviation}: {self.title}")


class Professor(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    rating = models.FloatField()
    difficulty_level = models.FloatField()
    would_take_again = models.FloatField()
    
    def __str__(self):
        return (f"{self.id}: {self.first_name} {self.last_name}")


class Section(models.Model):
    crn = models.IntegerField(primary_key=True)
    course = models.CharField(max_length=100)
    title = models.CharField(max_length=100, default="")
    class_type = models.CharField(max_length=100)
    modality = models.CharField(max_length=100)
    credit_hours = models.CharField(max_length=100)
    capacity = models.CharField(max_length=100)
    # professor = models.ForeignKey("Professor", on_delete=models.CASCADE)
    professor = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    exam_code = models.CharField(max_length=100)
    avg_gpa = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return (f"{self.crn}: {self.course}")

    
class SectionTime(models.Model):
    crn = models.ForeignKey("Section", on_delete=models.CASCADE)
    days = models.CharField(max_length=100)
    begin_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self):
        return (f"{self.crn}: {self.days} {self.begin_time} - {self.end_time}")
    
    # Define a less-than method to compare SectionTime instances
    def __lt__(self, other):
        if self.begin_time == other.begin_time:
            return self.end_time < other.end_time
        return self.begin_time < other.begin_time
    
    def __gt__(self, other):
        if self.begin_time == other.begin_time:
            return self.end_time > other.end_time
        return self.begin_time > other.begin_time
    
    def __hash__(self):
        return hash((self.crn_id, self.days, self.begin_time, self.end_time))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return (self.crn_id, self.days, self.begin_time, self.end_time) == \
            (other.crn_id, other.days, other.begin_time, other.end_time)


class User(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return (f"{self.id}: {self.first_name} {self.last_name}")


class Preference(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    tod_preference = models.CharField(max_length=100)
    dow_preference = models.CharField(max_length=100)


class Weight(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    tod_weight = models.FloatField()
    dow_weight = models.FloatField()
    prof_weight = models.FloatField()


class Schedule(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    crns = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    score = models.FloatField()


class ScheduleLog(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    crns = models.JSONField()
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
class GradeDistribution(models.Model):
    academic_year = models.CharField(max_length=100)
    term = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    full_course = models.CharField(max_length=100)
    professor = models.CharField(max_length=100)
    gpa = models.FloatField()
    a = models.FloatField(null=True, blank=True)
    a_minus = models.FloatField(null=True, blank=True)
    b_plus = models.FloatField(null=True, blank=True)
    b = models.FloatField(null=True, blank=True)
    b_minus = models.FloatField(null=True, blank=True)
    c_plus = models.FloatField(null=True, blank=True)
    c = models.FloatField(null=True, blank=True)
    c_minus = models.FloatField(null=True, blank=True)
    d_plus = models.FloatField(null=True, blank=True)
    d = models.FloatField(null=True, blank=True)
    d_minus = models.FloatField(null=True, blank=True)
    f = models.FloatField(null=True, blank=True)
    withdraws = models.FloatField(null=True, blank=True)
    graded_enrollment = models.FloatField(null=True, blank=True)
    crn = models.CharField(max_length=100)
    credit_hours = models.IntegerField()
    
class SectionOpenOrClosed(models.Model):
    crn = models.IntegerField(primary_key=True)
    course = models.CharField(max_length=100)
    title = models.CharField(max_length=100, default="")
    class_type = models.CharField(max_length=100)
    modality = models.CharField(max_length=100)
    credit_hours = models.CharField(max_length=100)
    capacity = models.CharField(max_length=100)
    # professor = models.ForeignKey("Professor", on_delete=models.CASCADE)
    professor = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    exam_code = models.CharField(max_length=100)
    avg_gpa = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return (f"{self.crn}: {self.course}")
    
class SectionTimeOpenOrClosed(models.Model):
    crn = models.ForeignKey("SectionOpenOrClosed", on_delete=models.CASCADE)
    days = models.CharField(max_length=100)
    begin_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self):
        return (f"{self.crn}: {self.days} {self.begin_time} - {self.end_time}")
    
    # Define a less-than method to compare SectionTime instances
    def __lt__(self, other):
        if self.begin_time == other.begin_time:
            return self.end_time < other.end_time
        return self.begin_time < other.begin_time
    
    def __gt__(self, other):
        if self.begin_time == other.begin_time:
            return self.end_time > other.end_time
        return self.begin_time > other.begin_time
    
    def __hash__(self):
        return hash((self.crn_id, self.days, self.begin_time, self.end_time))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return (self.crn_id, self.days, self.begin_time, self.end_time) == \
            (other.crn_id, other.days, other.begin_time, other.end_time)
    

