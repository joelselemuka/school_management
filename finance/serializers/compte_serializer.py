"""Serializers pour les comptes élèves."""

from rest_framework import serializers
from finance.models import CompteEleve, DetteEleve, Paiement
from admission.models import Inscription


class DetteEleveSerializer(serializers.ModelSerializer):
    """Serializer pour les dettes élèves."""
    
    class Meta:
        model = DetteEleve
        fields = ['id', 'frais', 'montant_initial', 'montant_reduit', 'montant_paye', 'montant_du', 'statut', 'last_payment_at', 'created_at']
        read_only_fields = ['id', 'created_at']


class PaiementSerializer(serializers.ModelSerializer):
    """Serializer pour les paiements."""
    
    class Meta:
        model = Paiement
        fields = ['id', 'reference', 'montant', 'mode', 'statut', 'created_at', 'confirmed_at']
        read_only_fields = ['id', 'created_at']


class CompteEleveSerializer(serializers.ModelSerializer):
    """Serializer pour les comptes élèves."""

    dettes = serializers.SerializerMethodField()
    paiements = serializers.SerializerMethodField()
    solde = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    eleve_nom = serializers.SerializerMethodField()
    eleve_classe = serializers.SerializerMethodField()
    solde_display = serializers.SerializerMethodField()
    statut_financier = serializers.SerializerMethodField()
    
    class Meta:
        model = CompteEleve
        fields = [
            'id', 'eleve', 'eleve_nom', 'eleve_classe', 'solde', 'solde_display',
            'statut_financier', 'dettes', 'paiements', 'updated_at'
        ]
        read_only_fields = ['id', 'solde', 'solde_display', 'statut_financier', 'updated_at']

    def get_dettes(self, obj):
        dettes = getattr(obj.eleve, "prefetched_dettes", None)
        if dettes is None:
            dettes = obj.eleve.detteeleve_set.all()
        return DetteEleveSerializer(dettes, many=True).data

    def get_paiements(self, obj):
        paiements = getattr(obj.eleve, "prefetched_paiements", None)
        if paiements is None:
            paiements = obj.eleve.paiement_set.all()
        return PaiementSerializer(paiements, many=True).data

    def get_eleve_nom(self, obj):
        user = getattr(obj.eleve, "user", None)
        if user:
            return user.full_name
        return str(obj.eleve)

    def get_eleve_classe(self, obj):
        inscriptions = getattr(obj.eleve, "prefetched_inscriptions", None)
        if inscriptions is None:
            inscriptions = (
                Inscription.objects
                .filter(eleve=obj.eleve)
                .select_related("classe")
                .order_by("-date_inscription")
            )
        inscription = inscriptions[0] if inscriptions else None
        if not inscription or not inscription.classe:
            return None
        return inscription.classe.nom

    def get_solde_display(self, obj):
        try:
            return f"{obj.solde:.2f}"
        except Exception:
            return "0.00"

    def get_statut_financier(self, obj):
        return "A jour" if obj.solde <= 0 else "En dette"
