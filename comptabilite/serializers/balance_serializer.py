from rest_framework import serializers

class BalanceSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    total_debit = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    solde = serializers.DecimalField(max_digits=15, decimal_places=2)
