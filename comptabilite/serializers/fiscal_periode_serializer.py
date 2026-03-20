

from rest_framework import serializers

from comptabilite.models.fiscal import FiscalPeriod


class FiscalPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalPeriod
        fields = [
            "id",
            "year",
            "month",
            "start_date",
            "end_date",
            "status",
            "closed_at",
            "closed_by",
        ]
        read_only_fields = ["status", "closed_at", "closed_by"]
