from rest_framework import serializers
from academics.models import Classe
from core.models import AnneeAcademique
from users.models import Personnel
from academics.services.classe_service import ClasseService


class ClasseSerializer(serializers.ModelSerializer):

    class Meta:

        model = Classe

        fields = "__all__"
        
        read_only_fields = ["annee_academique"]



class ClasseCreateSerializer(serializers.Serializer):

    nom = serializers.CharField()

    niveau = serializers.CharField()

    annee_academique = serializers.PrimaryKeyRelatedField(
        queryset=Classe._meta.get_field(
            "annee_academique"
        ).related_model.objects.all()
    )

    responsable = serializers.PrimaryKeyRelatedField(
        queryset=Classe._meta.get_field(
            "responsable"
        ).related_model.objects.all(),
        required=False,
        allow_null=True
    )



class ClasseUpdateSerializer(serializers.Serializer):

    nom = serializers.CharField(required=False)

    niveau = serializers.CharField(required=False)

    responsable = serializers.PrimaryKeyRelatedField(

        queryset=Classe._meta.get_field(
            "responsable"
        ).related_model.objects.all(),

        required=False,
        allow_null=True
    )


from rest_framework import serializers
from academics.models import Classe


class ClasseReadSerializer(serializers.ModelSerializer):

    annee_academique_nom = serializers.CharField(
        source="annee_academique.nom",
        read_only=True
    )


    class Meta:

        model = Classe

        fields = [

            "id",

            "nom",

            "niveau",

            "annee_academique_nom",
           

            "responsable"

           

        ]

        read_only_fields = fields