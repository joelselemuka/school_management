"""
URLs pour le module finance (paiements élèves, frais, dettes, factures, comptes).
Les endpoints de paie du personnel sont dans le module paie.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from finance.views.finance_views import (
    CompteEleveViewSet,
    DetteEleveViewSet,
    FactureViewSet,
    FinanceReportViewSet,
    FraisViewSet,
    PaiementViewSet,
)


router = DefaultRouter()
router.register(r'frais', FraisViewSet, basename='frais')
router.register(r'paiements', PaiementViewSet, basename='paiement')
router.register(r'dettes', DetteEleveViewSet, basename='dette')
router.register(r'factures', FactureViewSet, basename='facture')
router.register(r'comptes', CompteEleveViewSet, basename='compte-eleve')
router.register(r'reports', FinanceReportViewSet, basename='finance-report')

urlpatterns = [
    path('', include(router.urls)),
]
