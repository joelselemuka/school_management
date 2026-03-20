from rest_framework import serializers

from core.models import Periode


class PeriodeReadSerializer(serializers.ModelSerializer):

    class Meta:

        model = Periode

        fields = "__all__"



class PeriodeWriteSerializer(serializers.ModelSerializer):

    class Meta:

        model = Periode

        fields = ["nom","trimestre","annee_academique","date_debut","date_fin"]