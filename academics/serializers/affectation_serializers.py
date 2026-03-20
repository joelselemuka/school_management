from rest_framework import serializers
from academics.models import AffectationEnseignant


class AffectationReadSerializer(serializers.ModelSerializer):


    enseignant_nom = serializers.CharField(
        source="teacher.user.full_name",
        read_only=True
    )


    cours_nom = serializers.CharField(
        source="cours.nom",
        read_only=True
    )


    class Meta:

        model = AffectationEnseignant

        fields = "__all__"
        
        

class AffectationCreateSerializer(serializers.Serializer):

    teacher = serializers.PrimaryKeyRelatedField(
        queryset=AffectationEnseignant._meta.get_field(
            "teacher"
        ).related_model.objects.all()
    )


    cours = serializers.PrimaryKeyRelatedField(
        queryset=AffectationEnseignant._meta.get_field(
            "cours"
        ).related_model.objects.all()
    )
    
    role = serializers.ChoiceField(choices=[('titulaire','Titulaire'),('remplacant','Remplaçant')])

    start_date=serializers.DateField()
    end_date=serializers.DateField(required=False)




class AffectationUpdateSerializer(serializers.Serializer):

    teacher = serializers.PrimaryKeyRelatedField(
        queryset=AffectationEnseignant._meta.get_field(
            "teacher"
        ).related_model.objects.all(),
        required=False
    )
    
    cours = serializers.PrimaryKeyRelatedField(
        queryset=AffectationEnseignant._meta.get_field(
            "cours"
        ).related_model.objects.all(),
        required=False
    )
    
    role = serializers.CharField(required=False)
    start_date =serializers.DateField(required=False)
    end_date =serializers.DateField(required=False)



