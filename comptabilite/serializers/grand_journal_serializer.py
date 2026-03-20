from rest_framework import serializers


class JournalLineSerializer(serializers.Serializer):
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    debit = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit = serializers.DecimalField(max_digits=14, decimal_places=2)


class JournalEntrySerializer(serializers.Serializer):
    reference = serializers.CharField()
    date = serializers.DateTimeField()
    description = serializers.CharField()
    lines = JournalLineSerializer(many=True)
