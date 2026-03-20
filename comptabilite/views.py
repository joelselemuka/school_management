from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from common.permissions import IsAdminOnly, IsComptable
from common.role_services import RoleService
from comptabilite.models import Account, Expense, FiscalPeriod, Transaction
from comptabilite.permission import ComptabilitePermission
from comptabilite.serializers.account_serializer import AccountSerializer
from rest_framework.response import Response
from comptabilite.permission import IsAdminOrAccountant
from comptabilite.serializers.cash_journalier_serializer import CashJournalSerializer
from comptabilite.serializers.expense_serializer import ExpenseSerializer
from comptabilite.serializers.fiscal_periode_serializer import FiscalPeriodSerializer
from comptabilite.serializers.grand_journal_serializer import JournalEntrySerializer
from comptabilite.serializers.income_statement_serializer import IncomeStatementSerializer
from comptabilite.serializers.transaction_serializer import TransactionSerializer
from comptabilite.services.account_report_service import AccountingReportService
from comptabilite.services.cash_journalier_service import CashJournalService
from comptabilite.services.etat_finance_service import FinancialStatementService
from comptabilite.services.grand_journal_service import JournalService
from comptabilite.services.expenses_service import ExpenseService
from comptabilite.services.periode_service import PeriodService
from finance.services.finance_services import FinanceAnalyticsService
from common.cache_utils import CacheManager

class AccountViewSet(ModelViewSet):
    queryset = Account.objects.all().order_by("code")
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated, ComptabilitePermission]



class TrialBalanceView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrAccountant]

    def get(self, request):

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "date_from": date_from,
            "date_to": date_to,
        }
        cached = CacheManager.get("trial_balance", **cache_key_args)
        if cached is not None:
            return Response(cached)

        data = AccountingReportService.get_trial_balance(
            date_from=date_from,
            date_to=date_to,
        )

        CacheManager.set("trial_balance", data, **cache_key_args)
        return Response(data)

class CashFlowSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrAccountant]

    def get(self, request):

        period = request.query_params.get("period", "month")

        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "period": period,
        }
        cached = CacheManager.get("cash_flow_summary", **cache_key_args)
        if cached is not None:
            return Response(cached)

        data = AccountingReportService.get_cash_flow_summary(period)

        CacheManager.set("cash_flow_summary", data, **cache_key_args)
        return Response(data)


class DailyCashJournalView(APIView):
    permission_classes = [IsAuthenticated, IsComptable]

    def get(self, request):
        from django.utils.dateparse import parse_date

        date_str = request.query_params.get("date")

        if not date_str:
            return Response(
                {"detail": "Paramètre 'date' requis."},
                status=400,
            )

        date = parse_date(date_str)

        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "date": date_str,
        }
        cached = CacheManager.get("daily_cash_journal", **cache_key_args)
        if cached is not None:
            return Response(cached)

        data = CashJournalService.get_daily_cash(date)
        serializer = CashJournalSerializer(data)

        CacheManager.set("daily_cash_journal", serializer.data, **cache_key_args)
        return Response(serializer.data)


class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.select_related(
        "created_by",
        "validated_by",
    ).order_by("-date")

    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, ComptabilitePermission]
    
    def perform_create(self, serializer):
        if not RoleService.is_comptable(self.request.user):
            raise PermissionDenied(
                "Seul le comptable peut créer une dépense."
            )

        serializer.save(created_by=self.request.user)
        
        
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        expense = self.get_object()

        if not RoleService.is_admin(request.user):
            raise PermissionDenied(
                "Seul l'admin peut valider une dépense."
            )

        ExpenseService.approve_expense(expense, request.user)

        return Response({"status": "approved"})
    
    
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        expense = self.get_object()

        if not RoleService.is_admin(request.user):
            raise PermissionDenied()

        expense.statut = "REJECTED"
        expense.validated_by = request.user
        expense.validated_at = timezone.now()
        expense.save()

        return Response({"status": "rejected"})




class FinanceAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (RoleService.is_admin(request.user) or RoleService.is_comptable(request.user)):
            raise PermissionDenied()

        today = timezone.now().date()

        encaisse = FinanceAnalyticsService.total_encaisse(
            today, today
        )

        depense = FinanceAnalyticsService.total_depense(
            today, today
        )

        return Response({
            "encaisse_jour": encaisse,
            "depense_jour": depense,
            "resultat_jour": encaisse - depense,
        })



class FiscalPeriodViewSet(ModelViewSet):
    queryset = FiscalPeriod.objects.all()
    serializer_class = FiscalPeriodSerializer
    permission_classes = [IsComptable]

    def get_permissions(self):
        if self.action in ["close_period", "create", "update", "partial_update", "destroy"]:
            return [IsAdminOnly()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def close_period(self, request, pk=None):
        period = self.get_object()
        PeriodService.close_period(period, request.user)
        return Response({"detail": "Période clôturée."})



class GeneralJournalView(APIView):
    permission_classes = [IsAuthenticated, IsComptable]

    def get(self, request):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "date_from": date_from,
            "date_to": date_to,
        }
        cached = CacheManager.get("general_journal", **cache_key_args)
        if cached is not None:
            return Response(cached)

        data = JournalService.get_general_journal(
            date_from=date_from,
            date_to=date_to,
        )

        serializer = JournalEntrySerializer(data, many=True)
        CacheManager.set("general_journal", serializer.data, **cache_key_args)
        return Response(serializer.data)



class GeneralLedgerView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrAccountant]

    def get(self, request, account_id):

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "account_id": account_id,
            "date_from": date_from,
            "date_to": date_to,
        }
        cached = CacheManager.get("general_ledger", **cache_key_args)
        if cached is not None:
            return Response(cached)

        data = AccountingReportService.get_general_ledger(
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
        )

        CacheManager.set("general_ledger", data, **cache_key_args)
        return Response(data)


class IncomeStatementView(APIView):
    permission_classes = [IsAuthenticated, IsComptable]

    def get(self, request):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "date_from": date_from,
            "date_to": date_to,
        }
        cached = CacheManager.get("income_statement", **cache_key_args)
        if cached is not None:
            return Response(cached)

        data = FinancialStatementService.get_income_statement(
            date_from=date_from,
            date_to=date_to,
        )

        serializer = IncomeStatementSerializer(data)
        CacheManager.set("income_statement", serializer.data, **cache_key_args)
        return Response(serializer.data)


class TransactionViewSet(ReadOnlyModelViewSet):
    queryset = (
        Transaction.objects
        .prefetch_related("lines__account")
        .order_by("-date")
    )

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, ComptabilitePermission]





