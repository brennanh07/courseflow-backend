from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from scheduler.models import Subject, Professor, Section, SectionTime, User, Preference, Weight, Schedule, ScheduleLog
from scheduler.serializers import (
    SubjectSerializer, ProfessorSerializer, SectionSerializer, SectionTimeSerializer, UserSerializer, PreferenceSerializer, 
    WeightSerializer, ScheduleSerializer, ScheduleLogSerializer, ScheduleInputSerializer
)

from django.http import JsonResponse
from main import process_schedules
# from logging_config import loggers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# logger = loggers['views']

class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    
class ProfessorViewSet(viewsets.ModelViewSet):
    queryset = Professor.objects.all()
    serializer_class = ProfessorSerializer
    
class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    
class SectionTimeViewSet(viewsets.ModelViewSet):
    queryset = SectionTime.objects.all()
    serializer_class = SectionTimeSerializer
    
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
class PreferenceViewSet(viewsets.ModelViewSet):
    queryset = Preference.objects.all()
    serializer_class = PreferenceSerializer
    
class WeightViewSet(viewsets.ModelViewSet):
    queryset = Weight.objects.all()
    serializer_class = WeightSerializer
    
class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    
class ScheduleLogViewSet(viewsets.ModelViewSet):
    queryset = ScheduleLog.objects.all()
    serializer_class = ScheduleLogSerializer
    
@method_decorator(csrf_exempt, name='dispatch')
class GenerateScheduleView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        # logger.info(f"Received schedule generation request: {request.data}")
        serializer = ScheduleInputSerializer(data=request.data)
        
        if serializer.is_valid():
            user_input = serializer.validated_data
            courses = user_input.get("courses")
            breaks = user_input.get("breaks")
            
            
            preferences = {
                "preferred_days": user_input.get("preferred_days"),
                "preferred_time": user_input.get("preferred_time"),
                "day_weight": user_input.get("day_weight"),
                "time_weight": user_input.get("time_weight"),
            }
            
            # logger.debug(f"Processed user input: courses={courses}, breaks={breaks}, preferences={preferences}")
            
            try:
                # Generate, score, and format schedules
                generated_schedules = process_schedules(
                    courses=courses,
                    breaks=breaks,
                    preferences=preferences,
                    max_schedules=10
                )
                # logger.info(f"Successfully generated {len(generated_schedules)} schedules")
                return JsonResponse({"schedules": generated_schedules}, status=status.HTTP_200_OK)
            
            except Exception as e:
                # logger.error(f"Error generating schedules: {str(e)}")
                # logger.exception("Full traceback:")
                return Response({"error": f"Failed to generate schedules: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # logger.warning(f"Invalid input data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
