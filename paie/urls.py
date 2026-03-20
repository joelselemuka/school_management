"""
URLs du module Paie.

Préfixe : /api/v1/paie/  (ou /api/paie/ pour rétrocompatibilité)

Endpoints :
  /paie/contrats/                     GET, POST
  /paie/contrats/{id}/                GET, PATCH
  /paie/contrats/{id}/resilier/       POST
  /paie/contrats/{id}/simuler/        POST
  /paie/contrats/actif_personnel/     GET ?personnel_id=X

  /paie/bulletins/                    GET, POST
  /paie/bulletins/{id}/               GET
  /paie/bulletins/{id}/valider/       POST
  /paie/bulletins/{id}/payer/         POST  ← crée + comptabilise en OHADA
  /paie/bulletins/by_personnel/       GET ?personnel_id=X
  /paie/bulletins/masse/              POST

  /paie/salaires/                     GET
  /paie/salaires/{id}/                GET
  /paie/salaires/{id}/confirmer/      POST
  /paie/salaires/{id}/annuler/        POST
  /paie/salaires/by_personnel/        GET ?personnel_id=X
  /paie/salaires/statistiques/        GET
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from paie.views.contrat_views import ContratEmployeViewSet
from paie.views.bulletin_views import BulletinSalaireViewSet
from paie.views.paiement_views import PaiementSalaireViewSet


router = DefaultRouter()
router.register(r"contrats", ContratEmployeViewSet, basename="paie-contrat")
router.register(r"bulletins", BulletinSalaireViewSet, basename="paie-bulletin")
router.register(r"salaires", PaiementSalaireViewSet, basename="paie-salaire")

urlpatterns = [
    path("", include(router.urls)),
]
