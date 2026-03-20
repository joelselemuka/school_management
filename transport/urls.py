from django.urls import path, include
from rest_framework.routers import DefaultRouter
from transport.views import (
    BusViewSet, ArretBusViewSet, ItineraireViewSet, 
    ArretItineraireViewSet, AffectationEleveTransportViewSet,
    AffectationChauffeurViewSet, DashboardChauffeurView
)

router = DefaultRouter()
router.register(r'bus', BusViewSet, basename='bus')
router.register(r'arrets', ArretBusViewSet, basename='arrets')
router.register(r'itineraires', ItineraireViewSet, basename='itineraires')
router.register(r'arrets-itineraire', ArretItineraireViewSet, basename='arrets-itineraire')
router.register(r'affectations', AffectationEleveTransportViewSet, basename='affectations')
router.register(r'affectations-chauffeurs', AffectationChauffeurViewSet, basename='affectations-chauffeurs')

urlpatterns = [
    path('dashboard-chauffeur/', DashboardChauffeurView.as_view(), name='dashboard-chauffeur'),
    path('', include(router.urls)),
]
