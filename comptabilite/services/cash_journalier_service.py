


from comptabilite.models.transaction_line import TransactionLine


class CashJournalService:

    CASH_ACCOUNT_CODE = "101"

    @staticmethod
    def get_daily_cash(date):

        qs = TransactionLine.objects.filter(
            account__code=CashJournalService.CASH_ACCOUNT_CODE,
            transaction__created_at__date=date,
        )

        from django.db.models import Sum, DecimalField
        from django.db.models.functions import Coalesce

        debit = qs.aggregate(
            total=Coalesce(Sum("debit"), 0, output_field=DecimalField())
        )["total"]

        credit = qs.aggregate(
            total=Coalesce(Sum("credit"), 0, output_field=DecimalField())
        )["total"]

        return {
            "date": date,
            "cash_in": debit,
            "cash_out": credit,
            "net_cash": debit - credit,
        }
