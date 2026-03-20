from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta

from comptabilite.models.transaction_line import TransactionLine


class AccountingReportService:

    # ===============================
    # GRAND LIVRE
    # ===============================
    @staticmethod
    def get_general_ledger(account_id, date_from=None, date_to=None):

        qs = TransactionLine.objects.select_related(
            "transaction",
            "account"
        ).filter(account_id=account_id)

        if date_from:
            qs = qs.filter(transaction__created_at__date__gte=date_from)

        if date_to:
            qs = qs.filter(transaction__created_at__date__lte=date_to)

        qs = qs.order_by("transaction__created_at", "id")

        balance = 0
        ledger = []

        for line in qs:
            balance += float(line.debit) - float(line.credit)

            ledger.append({
                "date": line.transaction.created_at,
                "reference": line.transaction.reference,
                "description": line.transaction.description,
                "debit": line.debit,
                "credit": line.credit,
                "running_balance": balance,
            })

        return ledger

    # ===============================
    # BALANCE COMPTABLE
    # ===============================
    @staticmethod
    def get_trial_balance(date_from=None, date_to=None):

        qs = TransactionLine.objects.select_related("account")

        if date_from:
            qs = qs.filter(transaction__created_at__date__gte=date_from)

        if date_to:
            qs = qs.filter(transaction__created_at__date__lte=date_to)

        balances = (
            qs.values(
                "account_id",
                "account__code",
                "account__name",
                "account__type",
            )
            .annotate(
                total_debit=Coalesce(Sum("debit"), 0, output_field=DecimalField()),
                total_credit=Coalesce(Sum("credit"), 0, output_field=DecimalField()),
            )
            .order_by("account__code")
        )

        result = []
        for row in balances:
            balance = row["total_debit"] - row["total_credit"]

            result.append({
                "account_id": row["account_id"],
                "code": row["account__code"],
                "name": row["account__name"],
                "type": row["account__type"],
                "total_debit": row["total_debit"],
                "total_credit": row["total_credit"],
                "balance": balance,
            })

        return result

    # ===============================
    # STATISTIQUES FINANCIÈRES
    # ===============================
    @staticmethod
    def get_cash_flow_summary(period="month"):

        today = timezone.now().date()

        if period == "day":
            start = today
        elif period == "week":
            start = today - timedelta(days=7)
        elif period == "month":
            start = today.replace(day=1)
        elif period == "year":
            start = today.replace(month=1, day=1)
        else:
            raise ValueError("Période invalide")

        qs = TransactionLine.objects.filter(
            transaction__created_at__date__gte=start
        )

        total_debit = qs.aggregate(
            total=Coalesce(Sum("debit"), 0, output_field=DecimalField())
        )["total"]

        total_credit = qs.aggregate(
            total=Coalesce(Sum("credit"), 0, output_field=DecimalField())
        )["total"]

        return {
            "period": period,
            "start_date": start,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "net": total_debit - total_credit,
        }
