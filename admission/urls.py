"""
URLs pour le module admission.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from admission.views.admission_views import (
    AdmissionApplicationViewSet,
    InscriptionViewSet
)

router = DefaultRouter()
router.register(r'applications', AdmissionApplicationViewSet, basename='admission-application')
router.register(r'inscriptions', InscriptionViewSet, basename='inscription')

urlpatterns = [
    path('', include(router.urls)),
]
