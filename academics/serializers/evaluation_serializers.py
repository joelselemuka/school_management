from rest_framework import serializers
from academics.models import Evaluation
from common.role_services import User


class EvaluationReadSerializer(serializers.ModelSerializer):


    cours_nom = serializers.CharField(
        source="cours.nom",
        read_only=True
    )

    periode_nom = serializers.CharField(
        source="periode.nom",
        read_only=True
    )
    
    annee_academique_nom = serializers.CharField(
        source="annee_academique.nom",
        read_only=True
    )

    class Meta:

        model = Evaluation

        fields = "__all__"
        

class EvaluationCreateSerializer(serializers.Serializer):


    nom = serializers.CharField()


    cours = serializers.PrimaryKeyRelatedField(
        queryset=Evaluation._meta.get_field(
            "cours"
        ).related_model.objects.all()
    )
    
    periode = serializers.PrimaryKeyRelatedField(
        queryset=Evaluation._meta.get_field(
            "periode"
        ).related_model.objects.all()
    )
    
    annee_academique = serializers.PrimaryKeyRelatedField(
        queryset=Evaluation._meta.get_field(
            "annee_academique"
        ).related_model.objects.all()
    )

    type_evaluation=serializers.CharField()

    bareme = serializers.FloatField()
    
    poids = serializers.DecimalField(decimal_places=2, max_digits=5)
    
    created_by= serializers.PrimaryKeyRelatedField(
        queryset=User.objects.select_related("personnel_profile").filter(personnel_profile__fonction="enseignant")
    )


class EvaluationUpdateSerializer(serializers.Serializer):

    nom = serializers.CharField(required=False)

    bareme = serializers.FloatField(required=False)
    
    type_evaluation=serializers.CharField()
    



