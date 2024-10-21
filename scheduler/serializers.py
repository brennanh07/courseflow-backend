from rest_framework import serializers
from scheduler.models import Subject, Professor, Section, SectionTime, User, Preference, Weight, Schedule, ScheduleLog

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'

class ProfessorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Professor
        fields = '__all__'

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'

class SectionTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionTime
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preference
        fields = '__all__'

class WeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Weight
        fields = '__all__'

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = '__all__'

class ScheduleLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleLog
        fields = '__all__'
        
class BreakSerializer(serializers.Serializer):
    begin_time = serializers.TimeField()
    end_time = serializers.TimeField()
        
class ScheduleInputSerializer(serializers.Serializer):
    courses = serializers.ListField(child=serializers.CharField())
    breaks = serializers.ListField(child=BreakSerializer(), allow_empty=True)
    preferred_days = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    preferred_time = serializers.CharField()
    day_weight = serializers.FloatField()
    time_weight = serializers.FloatField()
    