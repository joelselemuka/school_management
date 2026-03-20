"""
URLs pour le module core.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views.analytics_views import DashboardAnalyticsView
from core.views.core_views import (
    EcoleViewSet,
    AnneeAcademiqueViewSet,
    PeriodeViewSet,
    ReglePromotionViewSet
)

router = DefaultRouter()
router.register(r'ecole', EcoleViewSet, basename='ecole')
router.register(r'annees-academiques', AnneeAcademiqueViewSet, basename='annee-academique')
router.register(r'periodes', PeriodeViewSet, basename='periode')
router.register(r'regles-promotion', ReglePromotionViewSet, basename='regle-promotion')
urlpatterns = [
    path('analytics/dashboard/', DashboardAnalyticsView.as_view(), name='analytics-dashboard'),
    path('', include(router.urls)),
]
