from rest_framework import serializers
from core.models import AnneeAcademique


class AnneeAcademiqueReadSerializer(serializers.ModelSerializer):

    class Meta:

        model = AnneeAcademique

        fields = "__all__"



class AnneeAcademiqueWriteSerializer(serializers.ModelSerializer):

    class Meta:

        model = AnneeAcademique

        fields = [
            "nom",
            "date_debut",
            "date_fin",
            "date_debut_inscriptions",
            "date_fin_inscriptions",
            "actif",
        ]