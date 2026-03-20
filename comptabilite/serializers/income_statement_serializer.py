
from rest_framework import serializers
class IncomeStatementSerializer(serializers.Serializer):
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    expense = serializers.DecimalField(max_digits=14, decimal_places=2)
    net_result = serializers.DecimalField(max_digits=14, decimal_places=2)
