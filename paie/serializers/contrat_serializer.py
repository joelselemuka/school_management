"""
Serializers pour les contrats d'embauche et les renouvellements.
"""

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone

from paie.models import ContratEmploye, RenouvellementContrat


class ContratEmployeSerializer(serializers.ModelSerializer):
    """Serializer complet — utilisé pour CREATE, RETRIEVE et UPDATE."""

    personnel_nom = serializers.CharField(source="personnel.__str__", read_only=True)
    personnel_fonction = serializers.CharField(source="personnel.fonction", read_only=True)
    salaire_journalier = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    statut_effectif = serializers.CharField(read_only=True)
    created_by_nom = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = ContratEmploye
        fields = [
            "id",
            "personnel",
            "personnel_nom",
            "personnel_fonction",
            "type_contrat",
            "poste",
            "date_debut",
            "date_fin",
            "salaire_base",
            "nb_jours_ouvrable",
            "taux_retenue_absence",
            "taux_heure_supplementaire",
            "prime_motivation",
            "statut",
            "statut_effectif",
            "observations",
            "salaire_journalier",
            "days_until_expiry",
            "is_expiring_soon",
            "is_expired",
            "created_by",
            "created_by_nom",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "created_by",
            "created_at",
            "updated_at",
            "salaire_journalier",
            "days_until_expiry",
            "is_expiring_soon",
            "is_expired",
            "statut_effectif",
        )

    def validate(self, attrs):
        date_debut = attrs.get("date_debut")
        date_fin = attrs.get("date_fin")
        type_contrat = attrs.get("type_contrat", "CDI")

        if type_contrat in ("CDD", "STAGE", "INTERIM") and not date_fin:
            raise serializers.ValidationError(
                {"date_fin": f"La date de fin est obligatoire pour un contrat {type_contrat}."}
            )

        if date_debut and date_fin and date_fin <= date_debut:
            raise serializers.ValidationError(
                {"date_fin": "La date de fin doit être postérieure à la date de début."}
            )
        return attrs

    def validate_salaire_base(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError("Le salaire de base ne peut pas être négatif.")
        return value


class ContratEmployeListSerializer(serializers.ModelSerializer):
    """Serializer allégé pour les listes (performance)."""

    personnel_nom = serializers.CharField(source="personnel.__str__", read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ContratEmploye
        fields = [
            "id",
            "personnel",
            "personnel_nom",
            "type_contrat",
            "poste",
            "date_debut",
            "date_fin",
            "salaire_base",
            "prime_motivation",
            "statut",
            "days_until_expiry",
            "is_expiring_soon",
            "is_expired",
            "created_at",
        ]


class SimulationSalaireSerializer(serializers.Serializer):
    """
    Serializer pour la simulation de salaire (sans créer de bulletin).
    Utilisé par l'action POST /paie/contrats/{id}/simuler/.
    """

    nb_jours_absence = serializers.IntegerField(min_value=0, max_value=31, default=0)
    nb_heures_supplementaires = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=Decimal("0"), default=Decimal("0")
    )
    prime_motivation = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )
    autres_primes = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), default=Decimal("0")
    )
    autres_retenues = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), default=Decimal("0")
    )


class RenouvelerContratSerializer(serializers.Serializer):
    """
    Serializer pour la demande de renouvellement de contrat.
    Utilisé par l'action POST /paie/contrats/{id}/renouveler/

    Seuls les champs modifiés sont obligatoires. Le reste est copié depuis l'ancien contrat.
    """

    date_debut = serializers.DateField(
        help_text="Date de début du nouveau contrat (obligatoire)"
    )
    date_fin = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Nouvelle date de fin (obligatoire pour CDD/STAGE/INTERIM)",
    )
    salaire_base = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        help_text="Nouveau salaire de base (si non fourni, reprend celui de l'ancien contrat)",
    )
    prime_motivation = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        help_text="Nouvelle prime de motivation mensuelle",
    )
    taux_retenue_absence = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        required=False,
    )
    taux_heure_supplementaire = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
    )
    nb_jours_ouvrable = serializers.IntegerField(
        min_value=1,
        max_value=31,
        required=False,
    )
    observations = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Observations sur le renouvellement",
    )
    motif = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Motif du renouvellement",
    )

    def validate(self, attrs):
        date_debut = attrs.get("date_debut")
        date_fin = attrs.get("date_fin")

        if date_debut and date_fin and date_fin <= date_debut:
            raise serializers.ValidationError(
                {"date_fin": "La date de fin doit être postérieure à la date de début."}
            )

        if date_debut and date_debut < timezone.now().date():
            raise serializers.ValidationError(
                {"date_debut": "La date de début du renouvellement ne peut pas être dans le passé."}
            )

        return attrs


class RenouvellementContratSerializer(serializers.ModelSerializer):
    """Serializer pour afficher l'historique des renouvellements."""

    ancien_contrat_id = serializers.IntegerField(source="ancien_contrat.id", read_only=True)
    nouveau_contrat_id = serializers.IntegerField(source="nouveau_contrat.id", read_only=True)
    personnel_nom = serializers.CharField(
        source="ancien_contrat.personnel.__str__", read_only=True
    )
    ancien_contrat_poste = serializers.CharField(
        source="ancien_contrat.poste", read_only=True
    )
    ancien_contrat_salaire = serializers.DecimalField(
        source="ancien_contrat.salaire_base",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    nouveau_contrat_salaire = serializers.DecimalField(
        source="nouveau_contrat.salaire_base",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    nouveau_contrat_date_fin = serializers.DateField(
        source="nouveau_contrat.date_fin", read_only=True
    )
    created_by_nom = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = RenouvellementContrat
        fields = [
            "id",
            "ancien_contrat_id",
            "nouveau_contrat_id",
            "personnel_nom",
            "ancien_contrat_poste",
            "ancien_contrat_salaire",
            "nouveau_contrat_salaire",
            "nouveau_contrat_date_fin",
            "date_renouvellement",
            "motif",
            "created_by",
            "created_by_nom",
            "created_at",
        ]
        read_only_fields = ("created_by", "created_at")
