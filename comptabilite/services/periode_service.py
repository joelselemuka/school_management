

from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from comptabilite.models import FiscalPeriod, TransactionLine

class PeriodService:

    @staticmethod
    def get_period_for_date(date):
        return FiscalPeriod.objects.get(
            start_date__lte=date,
            end_date__gte=date,
        )

    @staticmethod
    def assert_period_open(date):
        period = PeriodService.get_period_for_date(date)

        if period.status == FiscalPeriod.STATUS_CLOSED:
            raise ValidationError(
                "La période comptable est clôturée."
            )

        return period

    @staticmethod
    @transaction.atomic
    def close_period(period, user):
        if period.status == FiscalPeriod.STATUS_CLOSED:
            raise ValidationError("Période déjà clôturée.")

        # 🔒 vérifier équilibre global
        PeriodService._assert_global_balance(period)

        period.status = FiscalPeriod.STATUS_CLOSED
        period.closed_at = timezone.now()
        period.closed_by = user
        period.save(update_fields=["status", "closed_at", "closed_by"])

        return period

    @staticmethod
    def _assert_global_balance(period):
        from django.db.models import Sum
        from django.db.models.functions import Coalesce
        from django.db.models import DecimalField

        qs = TransactionLine.objects.filter(
            transaction__created_at__date__gte=period.start_date,
            transaction__created_at__date__lte=period.end_date,
        )

        total_debit = qs.aggregate(
            total=Coalesce(Sum("debit"), 0, output_field=DecimalField())
        )["total"]

        total_credit = qs.aggregate(
            total=Coalesce(Sum("credit"), 0, output_field=DecimalField())
        )["total"]

        if total_debit != total_credit:
            raise ValidationError(
                "Impossible de clôturer : écritures non équilibrées."
            )
