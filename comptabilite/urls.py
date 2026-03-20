from rest_framework.routers import DefaultRouter
from django.urls import include, path

from .views.rapports_views import RapportsComptablesViewSet, PlanComptableViewSet


router = DefaultRouter()

# Rapports OHADA
router.register(r"rapports", RapportsComptablesViewSet, basename='rapports-comptables')
router.register(r"plan-comptable", PlanComptableViewSet, basename='plan-comptable')


urlpatterns = [
    path("", include(router.urls)),
]





