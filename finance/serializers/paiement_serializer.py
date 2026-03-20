from rest_framework import serializers

from finance.models import Paiement, PaiementAllocation


class PaiementAllocationSerializer(serializers.ModelSerializer):

    frais = serializers.CharField(source="dette.frais.nom", read_only=True)

    class Meta:
        model = PaiementAllocation
        fields = ["id", "frais", "montant"]

class PaiementSerializer(serializers.ModelSerializer):

    allocations = PaiementAllocationSerializer(many=True, read_only=True)

    eleve_nom = serializers.CharField(source="eleve.__str__", read_only=True)

    class Meta:
        model = Paiement
        fields = "__all__"
        read_only_fields = (
            "reference",
            "statut",
            "created_by",
            "created_at",
        )  
        
class CreatePaiementSerializer(serializers.Serializer):

    eleve_id = serializers.IntegerField()
    montant = serializers.DecimalField(max_digits=12, decimal_places=2)
    mode = serializers.ChoiceField(choices=["CASH", "BANK", "MOBILE"])


