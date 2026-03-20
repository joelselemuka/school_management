"""
ViewSet pour les paiements de salaire (PaiementSalaire).

Endpoints :
  GET  /paie/salaires/                       → liste avec filtres
  GET  /paie/salaires/{id}/                  → détail
  POST /paie/salaires/{id}/confirmer/        → confirmer + comptabilisation
  POST /paie/salaires/{id}/annuler/          → annuler un paiement PENDING
  GET  /paie/salaires/by_personnel/          → historique d'un personnel
  GET  /paie/salaires/statistiques/          → stats agrégées
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q

from paie.models import PaiementSalaire
from paie.serializers.paiement_serializer import PaiementSalaireSerializer
from paie.services.salaire_service import SalaireService
from paie.permissions import CanManagePayroll

from common.cache_utils import CacheManager
from common.models import AuditLog


class PaiementSalaireViewSet(viewsets.GenericViewSet):
    """
    ViewSet pour la consultation et la gestion des paiements de salaire.

    La création d'un PaiementSalaire se fait via BulletinSalaireViewSet.payer().
    Ce ViewSet permet de confirmer des paiements BANK/MOBILE et de consulter l'historique.
    """

    queryset = PaiementSalaire.objects.all()
    serializer_class = PaiementSalaireSerializer
    permission_classes = [CanManagePayroll]
    filterset_fields = ["personnel", "mode", "statut", "annee", "mois", "annee_academique"]
    search_fields = ["reference", "personnel__nom", "personnel__postnom", "personnel__prenom"]
    ordering_fields = ["created_at", "montant", "confirmed_at", "annee", "mois"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return self.queryset.select_related(
            "personnel__user",
            "created_by",
            "confirmed_by",
            "annee_academique",
        )

    def list(self, request, *args, **kwargs):
        """Liste les paiements de salaire avec cache."""
        cache_key_args = {"user_id": getattr(request.user, "id", None), "params": dict(request.query_params)}
        cached = CacheManager.get("paie_salaires_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self.get_paginated_response(serializer.data).data
        else:
            serializer = self.get_serializer(qs, many=True)
            data = serializer.data

        CacheManager.set("paie_salaires_list", data, **cache_key_args, timeout=180)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        """Détail d'un paiement de salaire."""
        return Response(self.get_serializer(self.get_object()).data)

    # ── Actions métier ────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def confirmer(self, request, pk=None):
        """
        Confirme un paiement PENDING (mode BANK ou MOBILE).
        Déclenche la comptabilisation OHADA.
        """
        salaire = self.get_object()
        if salaire.statut != "PENDING":
            return Response(
                {"error": "Seuls les paiements en attente peuvent être confirmés"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = SalaireService.confirm_payment(salaire, request.user)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        CacheManager.invalidate_pattern("paie_salaires_list:*")
        AuditLog.log(user=request.user, action="update",
                     description=f"Paiement salaire confirmé : {salaire.reference}",
                     content_object=salaire, request=request)

        return Response(self.get_serializer(result).data)

    @action(detail=True, methods=["post"])
    def annuler(self, request, pk=None):
        """
        Annule un paiement PENDING.
        Un paiement CONFIRMED ne peut pas être annulé.
        """
        salaire = self.get_object()
        if salaire.statut == "CONFIRMED":
            return Response(
                {"error": "Un paiement confirmé ne peut pas être annulé"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if salaire.statut == "CANCELLED":
            return Response(
                {"error": "Ce paiement est déjà annulé"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        salaire.statut = "CANCELLED"
        salaire.save(update_fields=["statut"])
        CacheManager.invalidate_pattern("paie_salaires_list:*")

        AuditLog.log(user=request.user, action="update",
                     description=f"Paiement salaire annulé : {salaire.reference}",
                     content_object=salaire, request=request)

        return Response(self.get_serializer(salaire).data)

    @action(detail=False, methods=["get"])
    def by_personnel(self, request):
        """
        Historique des paiements d'un personnel.
        Query params : personnel_id (obligatoire), annee (optionnel)
        """
        personnel_id = request.query_params.get("personnel_id")
        if not personnel_id:
            return Response({"error": "personnel_id requis"}, status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().filter(personnel_id=personnel_id)
        annee = request.query_params.get("annee")
        if annee:
            qs = qs.filter(annee=annee)

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def statistiques(self, request):
        """
        Statistiques agrégées des paiements de salaire.
        Query params : annee, mois (optionnels)
        """
        qs = self.get_queryset()

        annee = request.query_params.get("annee")
        mois = request.query_params.get("mois")
        if annee:
            qs = qs.filter(annee=annee)
        if mois:
            qs = qs.filter(mois=mois)

        stats = qs.aggregate(
            total_paiements=Count("id"),
            total_montant=Sum("montant"),
            total_confirmes=Count("id", filter=Q(statut="CONFIRMED")),
            total_pending=Count("id", filter=Q(statut="PENDING")),
            total_annules=Count("id", filter=Q(statut="CANCELLED")),
            montant_confirme=Sum("montant", filter=Q(statut="CONFIRMED")),
        )

        return Response(stats)
