from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Parent, Personnel, User


from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed


class CustomTokenSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):

        identifier = attrs.get("username")
        password = attrs.get("password")

        user = authenticate(identifier=identifier, password=password)

        if not user:
            raise AuthenticationFailed("Identifiants invalides")

        data = super().validate({
            "username": user.username,
            "password": password
        })

        data["user_id"] = user.id
        data["role"] = user.role

        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer simple pour l'utilisateur."""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "full_name", "photo", "phone")
        read_only_fields = ("id", "username")
    
    def get_full_name(self, obj):
        """Retourne le nom complet."""
        return obj.get_full_name()


class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ("username", "email", "photo","phone")

class PersonnelSerializer(serializers.ModelSerializer):

    matricule = serializers.CharField(source="user.matricule")

    class Meta:

        model = Personnel

        fields = [

            "id",

            "matricule",

            "nom",

            "postnom",

            "prenom",

            "fonction",
            "specialite", 
            "telephone",
            "date_naissance" ,
            "lieu_naissance", 
            "adresse", 
            "sexe", 

        ]


class PersonnelCreateSerializer(serializers.Serializer):

    nom = serializers.CharField()

    postnom = serializers.CharField()

    prenom = serializers.CharField()

    fonction = serializers.CharField()

    telephone = serializers.CharField()

    adresse = serializers.CharField()

    email = serializers.EmailField()

    password = serializers.CharField(required=False, write_only=True)
  
    specialite = serializers.CharField()
    
    date_naissance = serializers.DateField()
    lieu_naissance = serializers.CharField()
    sexe = serializers.ChoiceField(choices=[("masculin", "Masculin"), ("féminin", "Féminin")])

class PersonnelUpdateSerializer(serializers.Serializer):

    nom = serializers.CharField(required=False)

    postnom = serializers.CharField(required=False)

    prenom = serializers.CharField(required=False)

    fonction = serializers.CharField(required=False)

    telephone = serializers.CharField(required=False)

    adresse = serializers.CharField(required=False)

    email = serializers.EmailField(required=False)

    password = serializers.CharField(required=False)
  
    specialite = serializers.CharField(required=False)
    
    date_naissance = serializers.DateField(required=False)
    lieu_naissance = serializers.CharField(required=False)
    sexe = serializers.CharField(required=False)

#************* PARENT ************

from rest_framework import serializers


class ParentCreateSerializer(serializers.Serializer):

    username = serializers.CharField()

    nom = serializers.CharField()

    postnom = serializers.CharField()

    prenom = serializers.CharField()

    telephone = serializers.CharField()

    adresse = serializers.CharField()
    
    sexe = serializers.CharField()

    email = serializers.EmailField(required=False)

    password = serializers.CharField(write_only=True, required=False)


class ParentSerializer(serializers.ModelSerializer):

    username = serializers.CharField(source="user.username")

    class Meta:

        model = Parent

        fields = [

            "id",

            "username",

            "nom",

            "postnom",

            "prenom",

            "telephone",
            
            "adresse",
            
            "sexe"

        ]


class ParentUpdateSerializer(serializers.Serializer):

    nom = serializers.CharField(required=False)

    postnom = serializers.CharField(required=False)

    prenom = serializers.CharField(required=False)

    telephone = serializers.CharField(required=False)

    adresse = serializers.CharField(required=False)

    email = serializers.EmailField(required=False)
    
    sexe = serializers.CharField(required=False)



    