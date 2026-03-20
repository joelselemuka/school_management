"""
Serializer pour les paiements de salaire.
"""

from rest_framework import serializers
from paie.models import PaiementSalaire


class PaiementSalaireSerializer(serializers.ModelSerializer):
    """Serializer complet pour PaiementSalaire."""

    personnel_nom = serializers.CharField(source="personnel.__str__", read_only=True)
    confirmed_by_nom = serializers.CharField(
        source="confirmed_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = PaiementSalaire
        fields = [
            "id",
            "reference",
            "personnel",
            "personnel_nom",
            "mois",
            "annee",
            "montant",
            "mode",
            "statut",
            "note",
            "annee_academique",
            "created_by",
            "confirmed_by",
            "confirmed_by_nom",
            "confirmed_at",
            "created_at",
        ]
        read_only_fields = (
            "reference",
            "statut",
            "created_by",
            "confirmed_by",
            "confirmed_at",
            "created_at",
        )
