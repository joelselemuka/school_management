"""
URLs pour les endpoints d'examens et salles.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from academics.views.exam_views import SalleViewSet
from academics.views.exam_views import (
    SessionExamenViewSet,
    PlanificationExamenViewSet,
    RepartitionExamenViewSet,
    ExamDistributionViewSet
)

router = DefaultRouter()
router.register(r'salles', SalleViewSet, basename='salle')
router.register(r'sessions-examen', SessionExamenViewSet, basename='session-examen')
router.register(r'planifications-examen', PlanificationExamenViewSet, basename='planification-examen')
router.register(r'repartitions-examen', RepartitionExamenViewSet, basename='repartition-examen')
router.register(r'exam-distribution', ExamDistributionViewSet, basename='exam-distribution')

urlpatterns = [
    path('', include(router.urls)),
]
