from rest_framework import serializers

from finance.models import Frais


class FraisSerializer(serializers.ModelSerializer):

    class Meta:
        model = Frais
        fields = "__all__"
        read_only_fields = ("created_at",)

