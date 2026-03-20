"""
ViewSet pour la gestion des contrats d'embauche.

Endpoints :
  GET    /paie/contrats/                         → liste (filtrable)
  POST   /paie/contrats/                         → créer un contrat
  GET    /paie/contrats/{id}/                    → détail
  PATCH  /paie/contrats/{id}/                    → modifier
  POST   /paie/contrats/{id}/resilier/           → résilier
  POST   /paie/contrats/{id}/simuler/            → simulation salaire net
  GET    /paie/contrats/actif_personnel/?personnel_id=X  → contrat actif d'un personnel
"""

from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from paie.models import ContratEmploye, RenouvellementContrat
from paie.serializers.contrat_serializer import (
    ContratEmployeSerializer,
    ContratEmployeListSerializer,
    SimulationSalaireSerializer,
    RenouvelerContratSerializer,
    RenouvellementContratSerializer,
)
from paie.services.contrat_service import ContratService
from paie.permissions import CanManagePayroll

from common.cache_utils import CacheManager
from common.models import AuditLog


class ContratEmployeViewSet(viewsets.GenericViewSet):
    """
    ViewSet pour la gestion des contrats d'embauche du personnel.

    Le DRH crée un contrat manuellement (POST) ou le modifie (PATCH).
    Un contrat par défaut est créé automatiquement lors de l'ajout du personnel.
    """

    queryset = ContratEmploye.objects.all()
    permission_classes = [CanManagePayroll]
    filterset_fields = ["personnel", "statut", "type_contrat"]
    search_fields = ["personnel__nom", "personnel__postnom", "personnel__prenom", "poste"]
    ordering_fields = ["created_at", "date_debut", "salaire_base"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ContratEmployeListSerializer
        return ContratEmployeSerializer

    def get_queryset(self):
        return self.queryset.select_related("personnel__user", "created_by")

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def list(self, request, *args, **kwargs):
        """Liste les contrats avec cache et pagination."""
        cache_key_args = {"user_id": getattr(request.user, "id", None), "params": dict(request.query_params)}
        cached = CacheManager.get("paie_contrats_list", **cache_key_args)
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

        CacheManager.set("paie_contrats_list", data, **cache_key_args, timeout=300)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        """Détail complet d'un contrat."""
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Crée un nouveau contrat. Refuse si un contrat ACTIF existe déjà."""
        serializer = ContratEmployeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            contrat = ContratService.creer_contrat(
                personnel=data["personnel"],
                type_contrat=data["type_contrat"],
                poste=data["poste"],
                date_debut=data["date_debut"],
                salaire_base=data["salaire_base"],
                user=request.user,
                date_fin=data.get("date_fin"),
                nb_jours_ouvrable=data.get("nb_jours_ouvrable", 26),
                taux_retenue_absence=data.get("taux_retenue_absence", Decimal("100.00")),
                taux_heure_supplementaire=data.get("taux_heure_supplementaire", Decimal("0")),
                prime_motivation=data.get("prime_motivation", Decimal("0")),
                observations=data.get("observations"),
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        CacheManager.invalidate_pattern("paie_contrats_list:*")
        AuditLog.log(user=request.user, action="create",
                     description=f"Contrat créé : {contrat}", content_object=contrat, request=request)

        return Response(ContratEmployeSerializer(contrat).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """Modifie partiellement les champs financiers d'un contrat."""
        contrat = self.get_object()
        serializer = ContratEmployeSerializer(contrat, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            ContratService.modifier_contrat(contrat=contrat, user=request.user, **serializer.validated_data)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        CacheManager.invalidate_pattern("paie_contrats_list:*")
        AuditLog.log(user=request.user, action="update",
                     description=f"Contrat modifié : {contrat}", content_object=contrat, request=request)

        return Response(ContratEmployeSerializer(contrat).data)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.partial_update(request, *args, **kwargs)

    # ── Actions métier ────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def resilier(self, request, pk=None):
        """Résilie un contrat actif."""
        contrat = self.get_object()
        try:
            ContratService.resilier_contrat(contrat, request.user)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        CacheManager.invalidate_pattern("paie_contrats_list:*")
        AuditLog.log(user=request.user, action="update",
                     description=f"Contrat résilié : {contrat}", content_object=contrat, request=request)

        return Response(ContratEmployeSerializer(contrat).data)

    @action(detail=True, methods=["post"])
    def simuler(self, request, pk=None):
        """
        Simule le calcul du salaire net sans créer de bulletin.

        Body : { nb_jours_absence, nb_heures_supplementaires, autres_primes, autres_retenues }
        """
        contrat = self.get_object()
        sim_serializer = SimulationSalaireSerializer(data=request.data)
        sim_serializer.is_valid(raise_exception=True)
        vd = sim_serializer.validated_data

        result = ContratService.simuler_salaire(
            contrat=contrat,
            nb_jours_absence=vd.get("nb_jours_absence", 0),
            nb_heures_supplementaires=vd.get("nb_heures_supplementaires", Decimal("0")),
            prime_motivation=vd.get("prime_motivation"),
            autres_primes=vd.get("autres_primes", Decimal("0")),
            autres_retenues=vd.get("autres_retenues", Decimal("0")),
        )
        return Response(result)

    @action(detail=True, methods=["post"])
    def renouveler(self, request, pk=None):
        """
        Renouvelle un contrat existant.

        Body : {
            date_debut (obligatoire),
            date_fin, salaire_base, prime_motivation,
            taux_retenue_absence, taux_heure_supplementaire,
            nb_jours_ouvrable, observations, motif
        }

        L'ancien contrat passe au statut RENOUVELE.
        Un nouveau contrat ACTIF est créé avec les nouvelles conditions.
        """
        ancien_contrat = self.get_object()
        serializer = RenouvelerContratSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        try:
            nouveau_contrat, renouvellement = ContratService.renouveler_contrat(
                ancien_contrat=ancien_contrat,
                user=request.user,
                date_debut=vd["date_debut"],
                date_fin=vd.get("date_fin"),
                salaire_base=vd.get("salaire_base"),
                prime_motivation=vd.get("prime_motivation"),
                taux_retenue_absence=vd.get("taux_retenue_absence"),
                taux_heure_supplementaire=vd.get("taux_heure_supplementaire"),
                nb_jours_ouvrable=vd.get("nb_jours_ouvrable"),
                observations=vd.get("observations"),
                motif=vd.get("motif"),
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        CacheManager.invalidate_pattern("paie_contrats_list:*")
        AuditLog.log(
            user=request.user, action="create",
            description=(
                f"Contrat renouvelé : #{ancien_contrat.id} → #{nouveau_contrat.id} "
                f"({ancien_contrat.personnel})"
            ),
            content_object=nouveau_contrat,
            metadata={
                "ancien_contrat_id": ancien_contrat.id,
                "nouveau_contrat_id": nouveau_contrat.id,
                "renouvellement_id": renouvellement.id,
            },
            request=request,
        )

        return Response({
            "nouveau_contrat": ContratEmployeSerializer(nouveau_contrat).data,
            "renouvellement": RenouvellementContratSerializer(renouvellement).data,
            "message": (
                f"Contrat #{ancien_contrat.id} renouvelé avec succès. "
                f"Nouveau contrat : #{nouveau_contrat.id}"
            ),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def historique_renouvellements(self, request):
        """
        Liste l'historique des renouvellements de contrat.
        Query params : personnel_id (optionnel)
        """
        qs = RenouvellementContrat.objects.select_related(
            "ancien_contrat__personnel__user",
            "nouveau_contrat",
            "created_by",
        ).order_by("-created_at")

        personnel_id = request.query_params.get("personnel_id")
        if personnel_id:
            qs = qs.filter(ancien_contrat__personnel_id=personnel_id)

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                RenouvellementContratSerializer(page, many=True).data
            )
        return Response(RenouvellementContratSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def actif_personnel(self, request):
        """
        Retourne le contrat actif d'un personnel.
        Query params : personnel_id (obligatoire)
        """
        personnel_id = request.query_params.get("personnel_id")
        if not personnel_id:
            return Response({"error": "personnel_id requis"}, status=status.HTTP_400_BAD_REQUEST)

        contrat = ContratEmploye.objects.filter(
            personnel_id=personnel_id, statut="ACTIF"
        ).select_related("personnel__user", "created_by").first()

        if not contrat:
            return Response(
                {"error": f"Aucun contrat actif pour le personnel {personnel_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(ContratEmployeSerializer(contrat).data)
