from rest_framework import serializers

from finance.models import DetteEleve



class DetteSerializer(serializers.ModelSerializer):

    eleve_nom = serializers.CharField(source="eleve.__str__", read_only=True)
    frais_nom = serializers.CharField(source="frais.nom", read_only=True)

    class Meta:
        model = DetteEleve
        fields = "__all__"
