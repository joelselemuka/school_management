from rest_framework import serializers
from admission.models import AdmissionApplication, AdmissionGuardian


class AdmissionGuardianSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdmissionGuardian
        fields = (
            "parent_nom",
            "parent_postnom",
            "parent_prenom",
            "parent_telephone",
            "parent_email",
            "parent_adresse",
            "parent_sexe",
            "lien",
        )
        
        

from .admission_serializers import AdmissionGuardianSerializer


class AdmissionApplicationSerializer(serializers.ModelSerializer):

    guardians = AdmissionGuardianSerializer(many=True)

    class Meta:
        model = AdmissionApplication
        fields = (
            "eleve_nom",
            "eleve_postnom",
            "eleve_prenom",
            "eleve_telephone",
            "eleve_email",
            "eleve_adresse",
            "eleve_sexe",
            "eleve_date_naissance",
            "eleve_lieu_naissance",
            "classe_souhaitee",
            "annee_academique",
            "guardians"
        )

    def create(self, validated_data):

        guardians_data = validated_data.pop("guardians")

        application = AdmissionApplication.objects.create(**validated_data)

        for g in guardians_data:
            AdmissionGuardian.objects.create(application=application, **g)

        return application

