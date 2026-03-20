from comptabilite.models.transaction_line import TransactionLine


class FinancialStatementService:

    @staticmethod
    def get_income_statement(date_from=None, date_to=None):

        qs = TransactionLine.objects.select_related("account")

        if date_from:
            qs = qs.filter(transaction__created_at__date__gte=date_from)

        if date_to:
            qs = qs.filter(transaction__created_at__date__lte=date_to)

        from django.db.models import Sum, DecimalField
        from django.db.models.functions import Coalesce

        revenue = qs.filter(account__type="REVENUE").aggregate(
            total=Coalesce(Sum("credit") - Sum("debit"), 0, output_field=DecimalField())
        )["total"]

        expense = qs.filter(account__type="EXPENSE").aggregate(
            total=Coalesce(Sum("debit") - Sum("credit"), 0, output_field=DecimalField())
        )["total"]

        net_result = revenue - expense

        return {
            "revenue": revenue,
            "expense": expense,
            "net_result": net_result,
        }
