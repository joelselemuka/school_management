
from rest_framework import serializers

from academics.models import Bulletin



class BulletinSerializer(serializers.ModelSerializer):

    eleve_nom = serializers.CharField(
        source="eleve.user.full_name",
        read_only=True
    )

    class Meta:

        model = Bulletin

        fields = [
            "id",
            "eleve",
            "eleve_nom",
            "classe",
            "periode",
            "moyenne_generale",
            "rang"
        ]

        read_only_fields = fields


class BulletinReadSerializer(serializers.ModelSerializer):


    eleve_nom = serializers.CharField(
        source="eleve.user.full_name",
        read_only=True
    )


    class Meta:

        model = Bulletin

        fields = "__all__"