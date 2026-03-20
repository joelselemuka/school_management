from rest_framework import serializers

from comptabilite.models.account import Account



class AccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = Account
        fields = "__all__"

