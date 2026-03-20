"""
URLs pour le module attendance.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from attendance.views.attendance_views import (
    HoraireViewSet,
    PresenceViewSet,
    SeanceViewSet,
    ClasseHoraireConfigViewSet,
    HoraireEnseignantViewSet,
)

router = DefaultRouter()
router.register(r'horaires', HoraireViewSet, basename='horaire')
router.register(r'presences', PresenceViewSet, basename='presence')
router.register(r'seances', SeanceViewSet, basename='seance')
router.register(r'classe-configs', ClasseHoraireConfigViewSet, basename='classe-config')
router.register(r'horaires-enseignants', HoraireEnseignantViewSet, basename='horaire-enseignant')

urlpatterns = [
    path('', include(router.urls)),
]
