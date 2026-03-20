


from django.utils import timezone
from comptabilite.models import Transaction, TransactionLine
from django.core.exceptions import ValidationError

from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError
from decimal import Decimal

from comptabilite.services.periode_service import PeriodService
from common.cache_utils import invalidate_comptabilite_reports_cache



class TransactionService:

    @staticmethod
    @db_transaction.atomic
    def create(reference, description, lines, user=None):
        """
        Crée une transaction équilibrée en partie double.
        """

        if not lines or len(lines) < 2:
            raise ValidationError("Une transaction doit avoir au moins deux lignes.")
        PeriodService.assert_period_open(timezone.now().date())

        # 🔁 idempotence
        if Transaction.objects.filter(reference=reference).exists():
            return Transaction.objects.get(reference=reference)

        total_debit = Decimal("0")
        total_credit = Decimal("0")

        for line in lines:
            debit = Decimal(line.get("debit", 0))
            credit = Decimal(line.get("credit", 0))

            if debit < 0 or credit < 0:
                raise ValidationError("Montants négatifs interdits.")

            total_debit += debit
            total_credit += credit

        # ⚖️ équilibre comptable
        if total_debit != total_credit:
            raise ValidationError(
                f"Transaction non équilibrée: debit={total_debit} credit={total_credit}"
            )

        # 🧾 création transaction
        transaction_obj = Transaction.objects.create(
            reference=reference,
            description=description,
            created_by=user,
        )

        # lignes
        for line in lines:
            TransactionLine.objects.create(
                transaction=transaction_obj,
                account=line["account"],
                debit=Decimal(line.get("debit", 0)),
                credit=Decimal(line.get("credit", 0)),
            )

        invalidate_comptabilite_reports_cache()

        return transaction_obj
