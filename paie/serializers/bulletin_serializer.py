"""
Serializers pour les bulletins de salaire.
"""

from rest_framework import serializers
from decimal import Decimal

from paie.models import BulletinSalaire


class BulletinSalaireSerializer(serializers.ModelSerializer):
    """Serializer complet pour CREATE et RETRIEVE."""

    personnel_nom = serializers.CharField(source="personnel.__str__", read_only=True)
    contrat_type = serializers.CharField(source="contrat.type_contrat", read_only=True)
    contrat_poste = serializers.CharField(source="contrat.poste", read_only=True)
    contrat_statut = serializers.CharField(source="contrat.statut", read_only=True)
    total_gains = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_retenues = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    created_by_nom = serializers.CharField(source="created_by.get_full_name", read_only=True)

    # Infos paiement associé (si le bulletin est PAYE)
    paiement_reference = serializers.CharField(
        source="paiement.reference", read_only=True, default=None
    )
    paiement_mode = serializers.CharField(
        source="paiement.mode", read_only=True, default=None
    )

    class Meta:
        model = BulletinSalaire
        fields = [
            "id",
            "contrat",
            "contrat_type",
            "contrat_poste",
            "contrat_statut",
            "personnel",
            "personnel_nom",
            "mois",
            "annee",
            # Éléments du calcul
            "salaire_base",
            "nb_jours_absence",
            "retenue_absence",
            "nb_heures_supplementaires",
            "montant_heures_sup",
            "prime_motivation",
            "autres_primes",
            "note_primes",
            "autres_retenues",
            "note_retenues",
            # Résumé financier
            "total_gains",
            "total_retenues",
            "salaire_net",
            # Statut et paiement
            "statut",
            "paiement",
            "paiement_reference",
            "paiement_mode",
            # Méta
            "created_by",
            "created_by_nom",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "retenue_absence",
            "montant_heures_sup",
            "total_gains",
            "total_retenues",
            "salaire_net",
            "created_by",
            "created_at",
            "updated_at",
            "paiement",
            "contrat_statut",
        )

    def validate(self, attrs):
        contrat = attrs.get("contrat")
        personnel = attrs.get("personnel")
        mois = attrs.get("mois")
        annee = attrs.get("annee")

        # Cohérence contrat ↔ personnel
        if contrat and personnel and contrat.personnel_id != personnel.id:
            raise serializers.ValidationError(
                {"contrat": "Ce contrat n'appartient pas au personnel sélectionné."}
            )

        # Contrat doit être actif (pas expiré, résilié, renouvelé ou suspendu)
        if contrat:
            if contrat.is_expired:
                raise serializers.ValidationError(
                    {
                        "contrat": (
                            f"Le contrat de {contrat.personnel} est expiré "
                            f"(date_fin: {contrat.date_fin}, statut: {contrat.statut}). "
                            "Veuillez renouveler le contrat avant de générer un bulletin."
                        )
                    }
                )
            if contrat.statut != "ACTIF":
                raise serializers.ValidationError(
                    {"contrat": f"Le contrat sélectionné n'est pas actif (statut: {contrat.statut})."}
                )

        # Unicité par personnel/mois/année
        instance = getattr(self, "instance", None)
        if mois and annee and personnel:
            qs = BulletinSalaire.objects.filter(personnel=personnel, mois=mois, annee=annee)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f"Un bulletin existe déjà pour ce personnel en {mois:02d}/{annee}."
                )

        return attrs


class BulletinSalaireListSerializer(serializers.ModelSerializer):
    """Serializer allégé pour les listes."""

    personnel_nom = serializers.CharField(source="personnel.__str__", read_only=True)

    class Meta:
        model = BulletinSalaire
        fields = [
            "id",
            "personnel",
            "personnel_nom",
            "mois",
            "annee",
            "salaire_base",
            "retenue_absence",
            "montant_heures_sup",
            "prime_motivation",
            "autres_primes",
            "autres_retenues",
            "salaire_net",
            "statut",
            "paiement",
            "created_at",
        ]
