from rest_framework import serializers

from comptabilite.models.transaction import Transaction
from comptabilite.models.transaction_line import TransactionLine


class TransactionLineSerializer(serializers.ModelSerializer):

    class Meta:
        model = TransactionLine
        fields = "__all__"



class TransactionSerializer(serializers.ModelSerializer):

    lines = TransactionLineSerializer(many=True, read_only=True)

    class Meta:
        model = Transaction
        fields = "__all__"
