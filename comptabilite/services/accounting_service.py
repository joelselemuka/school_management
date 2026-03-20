from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


from comptabilite.models import Account
from comptabilite.services.transaction_service import TransactionService

class AccountingService:

    @staticmethod
    @db_transaction.atomic
    def create_expense_transaction(expense):

        if expense.statut != "APPROVED":
            raise ValidationError(
                "Impossible de comptabiliser une dépense non validée."
            )

        # comptes
        expense_account = Account.objects.get(code="601")
        cash_account = Account.objects.get(code="101")

        amount = Decimal(expense.amount)

        return TransactionService.create(
            reference=expense.reference,
            description=f"Dépense: {expense.description}",
            user=expense.validated_by,
            lines=[
                {
                    "account": expense_account,
                    "debit": amount,
                    "credit": Decimal("0"),
                },
                {
                    "account": cash_account,
                    "debit": Decimal("0"),
                    "credit": amount,
                },
            ],
        )

    @staticmethod
    @db_transaction.atomic
    def create_payment_transaction(paiement):
        """
        Comptabilise un paiement scolaire confirme.
        """
        if paiement.statut != "CONFIRMED":
            raise ValidationError(
                "Impossible de comptabiliser un paiement non confirme."
            )

        income_account = Account.objects.get(code="7011")
        cash_account = AccountingService._get_cash_account_for_mode(paiement.mode)

        amount = Decimal(paiement.montant)

        return TransactionService.create(
            reference=paiement.reference,
            description=f"Paiement scolarite: {paiement.eleve}",
            user=paiement.confirmed_by or paiement.created_by,
            lines=[
                {
                    "account": cash_account,
                    "debit": amount,
                    "credit": Decimal("0"),
                },
                {
                    "account": income_account,
                    "debit": Decimal("0"),
                    "credit": amount,
                },
            ],
        )

    @staticmethod
    @db_transaction.atomic
    def create_salary_payment_transaction(paiement_salaire):
        """
        Comptabilise un paiement de salaire confirme.
        """
        if paiement_salaire.statut != "CONFIRMED":
            raise ValidationError(
                "Impossible de comptabiliser un salaire non confirme."
            )

        expense_account = AccountingService._get_salary_expense_account(
            paiement_salaire.personnel
        )
        cash_account = AccountingService._get_cash_account_for_mode(
            paiement_salaire.mode
        )

        amount = Decimal(paiement_salaire.montant)
        periode = f"{paiement_salaire.mois:02d}/{paiement_salaire.annee}"

        return TransactionService.create(
            reference=paiement_salaire.reference,
            description=(
                f"Salaire {paiement_salaire.personnel} - periode {periode}"
            ),
            user=paiement_salaire.confirmed_by or paiement_salaire.created_by,
            lines=[
                {
                    "account": expense_account,
                    "debit": amount,
                    "credit": Decimal("0"),
                },
                {
                    "account": cash_account,
                    "debit": Decimal("0"),
                    "credit": amount,
                },
            ],
        )

    @staticmethod
    def _get_cash_account_for_mode(mode):
        if mode == "CASH":
            return Account.objects.get(code="57")
        if mode == "BANK":
            return Account.objects.get(code="52")
        if mode == "MOBILE":
            return Account.objects.get(code="53")
        raise ValidationError("Mode de paiement inconnu.")

    @staticmethod
    def _get_salary_expense_account(personnel):
        fonction = getattr(personnel, "fonction", None)

        if fonction == "enseignant":
            return Account.objects.get(code="662")
        if fonction in {"comptable", "secretaire", "admin", "drh"}:
            return Account.objects.get(code="663")
        if fonction == "agent_entretien":
            return Account.objects.get(code="664")

        return Account.objects.get(code="6618")
