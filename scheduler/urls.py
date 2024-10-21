from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SubjectViewSet, ProfessorViewSet, SectionViewSet, SectionTimeViewSet, 
    UserViewSet, PreferenceViewSet, WeightViewSet, ScheduleViewSet, 
    ScheduleLogViewSet, GenerateScheduleView
)

# This is the router for the API
router = DefaultRouter()
router.register(r'subjects', SubjectViewSet)
router.register(r'professors', ProfessorViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'section-times', SectionTimeViewSet)
router.register(r'users', UserViewSet)
router.register(r'preferences', PreferenceViewSet)
router.register(r'weights', WeightViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'schedule-logs', ScheduleLogViewSet)

urlpatterns = [
    path('api/v1/', include(router.urls)), # this is the root URL
    path('api/v1/generate-schedules/', GenerateScheduleView.as_view(), name='generate-schedules'), # this is the endpoint for generating schedules
]