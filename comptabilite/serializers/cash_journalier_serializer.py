from rest_framework import serializers

class CashJournalSerializer(serializers.Serializer):
    date = serializers.DateField()
    cash_in = serializers.DecimalField(max_digits=14, decimal_places=2)
    cash_out = serializers.DecimalField(max_digits=14, decimal_places=2)
    net_cash = serializers.DecimalField(max_digits=14, decimal_places=2)
