from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsAdmin
from common.role_services import RoleService
from communication.services.notification_service import NotificationService
from finance.models import DetteEleve, Frais, Paiement
from finance.permissions.permissions import FinancePermission
from finance.serializers.dette_serializer import DetteSerializer
from finance.serializers.frais_serializers import FraisSerializer
from finance.serializers.paiement_serializer import CreatePaiementSerializer, PaiementSerializer
from finance.services.dette_service import DetteService
from finance.services.frais_service import FraisService
from finance.services.paiement_service import PaiementService
from finance.services.facture_service import FactureService
from users.models import Eleve


class FraisViewSet(ModelViewSet):
    queryset = Frais.objects.select_related(
        "classe",
        "annee_academique",
        "created_by",
    ).order_by("-created_at")

    serializer_class = FraisSerializer
    permission_classes = [IsAuthenticated, FinancePermission]

    def perform_create(self, serializer):
        if not RoleService.is_admin(self.request.user):
            raise PermissionDenied("Seul l'administrateur peut créer un frais.")

        data = serializer.validated_data
        frais = FraisService.create(
            nom=data['nom'],
            montant=data['montant'],
            classe=data['classe'],
            annee=data['annee_academique'],
            description=data.get('description', ""),
            obligatoire=data.get('obligatoire', True),
        )


        # 🔔 création automatique des dettes
        DetteService.create_for_frais(frais)

        # 🔔 notification
        NotificationService.notify_frais_created(frais)



class DetteViewSet(ReadOnlyModelViewSet):
    serializer_class = DetteSerializer
    permission_classes = [IsAuthenticated, FinancePermission]

    def get_queryset(self):
        user = self.request.user

        qs = DetteEleve.objects.select_related(
            "eleve",
            "frais",
        ).order_by("-created_at")

        if RoleService.is_admin(user) or RoleService.is_comptable(user):
            return qs

        if RoleService.is_eleve(user):
            return qs.filter(eleve=user.eleve_profile)

        if RoleService.is_parent(user):
            return qs.filter(
                eleve__parent_links__parent=user.parent_profile
            )

        return qs.none()


class PaiementViewSet(ModelViewSet):
    serializer_class = PaiementSerializer
    permission_classes = [IsAuthenticated, FinancePermission]

    def get_queryset(self):
        user = self.request.user

        qs = (
            Paiement.objects
            .select_related("eleve", "created_by", "confirmed_by")
            .prefetch_related("allocations__dette__frais")
            .order_by("-created_at")
        )

        if RoleService.is_admin(user) or RoleService.is_comptable(user):
            return qs

        if RoleService.is_eleve(user):
            return qs.filter(eleve=user.eleve_profile)

        if RoleService.is_parent(user):
            return qs.filter(
                eleve__parent_links__parent=user.parent_profile
            )

        return qs.none()

    def create(self, request):
        if not RoleService.is_comptable(request.user):
            raise PermissionDenied(
                "Seul le comptable peut enregistrer un paiement."
            )

        serializer = CreatePaiementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        eleve = get_object_or_404(
            Eleve,
            id=serializer.validated_data["eleve_id"]
        )

        paiement = PaiementService.create_paiement(
            eleve=eleve,
            montant=serializer.validated_data["montant"],
            mode=serializer.validated_data["mode"],
            user=request.user,
        )

        return Response(PaiementSerializer(paiement).data, status=201)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        paiement = self.get_object()

        if not RoleService.is_comptable(request.user):
            raise PermissionDenied("Action réservée au comptable.")

        if paiement.statut == "CONFIRMED":
            return Response({"detail": "Déjà confirmé."})

        PaiementService.apply_payment(paiement)

        paiement.statut = "CONFIRMED"
        paiement.confirmed_by = request.user
        paiement.confirmed_at = timezone.now()
        paiement.save()

        # facture
        FactureService.create_from_paiement(paiement)

        return Response({"status": "confirmed"})

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        paiement = self.get_object()

        if not RoleService.is_comptable(request.user):
            raise PermissionDenied("Action réservée au comptable.")

        if paiement.statut == "CONFIRMED":
            raise PermissionDenied("Impossible d'annuler un paiement confirmé.")

        paiement.statut = "CANCELLED"
        paiement.save()

        return Response({"status": "cancelled"})


class FinanceDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if RoleService.is_eleve(user):
            eleve = user.eleve_profile

        elif RoleService.is_parent(user):
            eleve = user.parent_profile.enfants.first().eleve

        else:
            raise PermissionDenied()

        total_dette = (
            DetteEleve.objects
            .filter(eleve=eleve)
            .aggregate(total=Sum("montant_du"))["total"] or 0
        )

        total_paye = (
            Paiement.objects
            .filter(eleve=eleve, statut="CONFIRMED")
            .aggregate(total=Sum("montant"))["total"] or 0
        )

        return Response({
            "total_dette": total_dette,
            "total_paye": total_paye,
            "solde": total_dette - total_paye,
        })


