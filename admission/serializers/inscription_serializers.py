from rest_framework import serializers

class GuardianInputSerializer(serializers.Serializer):
    nom = serializers.CharField()
    postnom = serializers.CharField()
    prenom = serializers.CharField()
    telephone = serializers.CharField(required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_null=True)
    adresse = serializers.CharField(required=False, allow_null=True)
    sexe = serializers.CharField()
    
    
    
class EleveInputSerializer(serializers.Serializer):

    nom = serializers.CharField()
    postnom = serializers.CharField()
    prenom = serializers.CharField()
    telephone = serializers.CharField(required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_null=True)
    adresse = serializers.CharField(required=False, allow_null=True)
    sexe = serializers.CharField()
    date_naissance = serializers.DateField(required=False)
    lieu_naissance = serializers.CharField(required=False)


class BureauInscriptionSerializer(serializers.Serializer):

    classe = serializers.IntegerField()
    annee = serializers.IntegerField()

    eleve = EleveInputSerializer()
    guardians = GuardianInputSerializer(many=True)


class InscriptionSerializer(serializers.Serializer):
    """Serializer pour les inscriptions existantes."""
    id = serializers.IntegerField(read_only=True)
    eleve = serializers.IntegerField()
    classe = serializers.IntegerField()
    annee_academique = serializers.IntegerField()
    date_inscription = serializers.DateTimeField(read_only=True)
    source = serializers.CharField(read_only=True)
    created_by = serializers.IntegerField(read_only=True)

