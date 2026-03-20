"""
Views du module Paie.
"""

from .contrat_views import ContratEmployeViewSet
from .bulletin_views import BulletinSalaireViewSet
from .paiement_views import PaiementSalaireViewSet

__all__ = [
    "ContratEmployeViewSet",
    "BulletinSalaireViewSet",
    "PaiementSalaireViewSet",
]
