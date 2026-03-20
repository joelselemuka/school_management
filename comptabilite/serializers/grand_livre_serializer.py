from rest_framework import serializers

class GrandLivreSerializer(serializers.Serializer):
    date = serializers.DateTimeField()
    reference = serializers.CharField()
    description = serializers.CharField()
    debit = serializers.DecimalField(max_digits=15, decimal_places=2)
    credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    solde_cumule = serializers.DecimalField(max_digits=15, decimal_places=2)
