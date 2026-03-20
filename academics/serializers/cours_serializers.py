from rest_framework import serializers
from academics.services.course_service import CoursService
from academics.models import Cours, Classe
from users.models import Personnel
from core.models import AnneeAcademique




class CoursSerializer(serializers.ModelSerializer):

    classe_nom = serializers.CharField(
        source="classe.nom",
        read_only=True
    )

    enseignant_nom = serializers.CharField(
        source="enseignant.user.full_name",
        read_only=True
    )

    class Meta:

        model = Cours

        fields = [

            "id",

            "nom",

            "classe",

            "classe_nom",

            "enseignant",

            "enseignant_nom",

            "coefficient"

        ]




class CoursCreateSerializer(serializers.Serializer):

    nom = serializers.CharField()
    
    code = serializers.CharField()

    classe = serializers.PrimaryKeyRelatedField(
        queryset=Cours._meta.get_field(
            "classe"
        ).related_model.objects.filter(actif=True)
    )
    
    annee_academique = serializers.PrimaryKeyRelatedField(
        queryset=Cours._meta.get_field(
            "annee_academique"
        ).related_model.objects.filter(actif=True)
    )
    coefficient = serializers.DecimalField(
        max_digits=5,
        decimal_places=2
    )
    
    def validate_coefficient(self, value):

        if value <= 0:

            raise serializers.ValidationError(
                "Coefficient doit être positif"
            )

        return value


class CoursUpdateSerializer(serializers.Serializer):

    nom = serializers.CharField(required=False)

    coefficient = serializers.DecimalField(

        max_digits=5,
        decimal_places=2,
        required=False
    )

    classe = serializers.PrimaryKeyRelatedField(
        queryset=Cours._meta.get_field(
            "classe"
        ).related_model.objects.filter(actif=True),
        required=False
    )
    
    annee_academique = serializers.PrimaryKeyRelatedField(
        queryset=Cours._meta.get_field(
            "annee_academique"
        ).related_model.objects.filter(actif=True),
        required=False
    )


class CoursReadSerializer(serializers.ModelSerializer):


    classe_nom = serializers.CharField(

        source="classe.nom",
        read_only=True
    )


    enseignant_nom = serializers.SerializerMethodField()


    class Meta:

        model = Cours

        fields = [

            "id",

            "nom",

            "coefficient",

            "classe",
            "classe_nom",

            "enseignant_nom",

            "annee_academique",

           
        ]

        read_only_fields = fields

    def get_enseignant_nom(self, obj):
        affectations = list(obj.affectations.all())
        if not affectations:
            return None

        titulaire = None
        for affectation in affectations:
            if affectation.role == "titulaire":
                titulaire = affectation
                break

        affectation = titulaire or affectations[0]
        teacher = getattr(affectation, "teacher", None)
        if not teacher:
            return None
        user = getattr(teacher, "user", None)
        return user.full_name if user else str(teacher)

