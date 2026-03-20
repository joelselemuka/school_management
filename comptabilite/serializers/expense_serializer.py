from rest_framework import serializers

from comptabilite.models.depense import Expense
from comptabilite.services.expenses_service import ExpenseService




class ExpenseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Expense
        fields = "__all__"

    def create(self, validated_data):

        return ExpenseService.create_expense(validated_data)
