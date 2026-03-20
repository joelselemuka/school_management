"""
URLs pour le module Events.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from events.views import EventViewSet, ActualiteViewSet, InscriptionEvenementViewSet

router = DefaultRouter()
router.register(r'evenements', EventViewSet, basename='evenement')
router.register(r'actualites', ActualiteViewSet, basename='actualite')
router.register(r'inscriptions', InscriptionEvenementViewSet, basename='inscription')

urlpatterns = [
    path('', include(router.urls)),
]
