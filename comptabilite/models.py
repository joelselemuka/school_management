from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.db.models import DecimalField


from django.utils import timezone
from django.db import transaction




class Account(models.Model):

    ACCOUNT_TYPES = (
        ("asset", "Asset"),
        ("liability", "Liability"),
        ("equity", "Equity"),
        ("income", "Income"),
        ("expense", "Expense"),
    )

    code = models.CharField(max_length=20, unique=True)

    name = models.CharField(max_length=255)

    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    



class Expense(models.Model):
    reference = models.CharField(max_length=50, unique=True)

    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    statut = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "En attente"),
            ("APPROVED", "Validée"),
            ("REJECTED", "Rejetée"),
        ],
        default="PENDING"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_expenses"
    )

    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="validated_expenses",
        on_delete=models.PROTECT
    )

    validated_at = models.DateTimeField(null=True, blank=True)

    date = models.DateTimeField(auto_now_add=True)


class Transaction(models.Model):

    reference = models.CharField(max_length=50, unique=True)

    description = models.TextField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_transactions",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reference
    
    class Meta:
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["reference"]),
        ]



class TransactionLine(models.Model):

    transaction = models.ForeignKey(
        Transaction,
        related_name="lines",
        on_delete=models.CASCADE
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT
    )

    debit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    credit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return f"{self.account.name}"
    
    class Meta:
        indexes = [
            models.Index(fields=["account"]),
            models.Index(fields=["transaction"]),
        ]


class FiscalPeriod(models.Model):
    STATUS_OPEN = "OPEN"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = (
        (STATUS_OPEN, "Ouvert"),
        (STATUS_CLOSED, "Clôturé"),
    )

    year = models.IntegerField()
    month = models.IntegerField()

    start_date = models.DateField()
    end_date = models.DateField()

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )

    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        unique_together = ("year", "month")
        ordering = ["-year", "-month"]


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







