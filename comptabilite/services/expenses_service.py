from datetime import timezone
from django.db import transaction as db_transaction

from comptabilite.models import Account, TransactionLine
from comptabilite.models.depense import Expense
from comptabilite.models.transaction import Transaction
from django.core.exceptions import ValidationError

from comptabilite.services.accounting_service import AccountingService
from common.cache_utils import invalidate_comptabilite_reports_cache



class ExpenseService:

    @staticmethod
    @db_transaction.atomic
    def approve_expense(expense, admin_user):
        if expense.statut != "PENDING":
            raise ValidationError("Dépense déjà traitée.")

        expense.statut = "APPROVED"
        expense.validated_by = admin_user
        expense.validated_at = timezone.now()
        expense.save()

        AccountingService.create_expense_transaction(expense)
        invalidate_comptabilite_reports_cache()
           
    @staticmethod
    @db_transaction.atomic
    def create_expense(data):

        expense = Expense.objects.create(**data)

        transaction = Transaction.objects.create(
            reference=expense.reference,
            description="Depense"
        )

        expense_account = Account.objects.get(code="601")

        cash_account = Account.objects.get(code="101")

        TransactionLine.objects.create(
            transaction=transaction,
            account=expense_account,
            debit=expense.amount
        )

        TransactionLine.objects.create(
            transaction=transaction,
            account=cash_account,
            credit=expense.amount
        )

        invalidate_comptabilite_reports_cache()

        return expense
