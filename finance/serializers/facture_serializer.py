"""Serializers pour les factures."""

from rest_framework import serializers
from finance.models import Facture
from finance.services.reference_service import ReferenceService


class FactureSerializer(serializers.ModelSerializer):
    """Serializer pour les factures."""

    eleve_nom = serializers.CharField(source="eleve.user.full_name", read_only=True)
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)

    class Meta:
        model = Facture
        fields = [
            "id",
            "numero",
            "paiement",
            "eleve",
            "eleve_nom",
            "montant",
            "pdf",
            "date_emission",
            "statut",
            "statut_display",
            "created_at",
        ]
        read_only_fields = ["id", "numero", "created_at"]


class FactureCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de factures."""

    class Meta:
        model = Facture
        fields = [
            "paiement",
            "eleve",
            "montant",
            "date_emission",
            "statut",
            "pdf",
        ]

    def create(self, validated_data):
        if "numero" not in validated_data:
            validated_data["numero"] = ReferenceService.generate("FACT")
        return super().create(validated_data)
