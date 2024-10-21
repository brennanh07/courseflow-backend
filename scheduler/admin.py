from django.contrib import admin
from .models import Subject, Professor, Section, SectionTime, User, Preference, Weight, Schedule, ScheduleLog

# Register your models here.
admin.site.register(Subject)