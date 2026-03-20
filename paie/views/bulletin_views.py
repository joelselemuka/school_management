"""
ViewSet pour les bulletins de salaire.

Workflow complet :
  1. POST /paie/bulletins/               → Génère un bulletin (statut: BROUILLON)
  2. POST /paie/bulletins/{id}/valider/  → Valide (statut: VALIDE)
  3. POST /paie/bulletins/{id}/payer/    → Paye + trace OHADA (statut: PAYE)

Autres endpoints :
  GET  /paie/bulletins/                         → liste avec filtres
  GET  /paie/bulletins/{id}/                    → détail
  GET  /paie/bulletins/by_personnel/            → historique d'un personnel
  POST /paie/bulletins/masse/                   → génération en masse
"""

from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from paie.models import ContratEmploye, BulletinSalaire
from paie.serializers.bulletin_serializer import BulletinSalaireSerializer, BulletinSalaireListSerializer
from paie.serializers.paiement_serializer import PaiementSalaireSerializer
from paie.services.bulletin_service import BulletinSalaireService
from paie.permissions import CanManagePayroll

from common.cache_utils import CacheManager
from common.models import AuditLog


class BulletinSalaireViewSet(viewsets.GenericViewSet):
    """
    ViewSet pour la gestion du cycle de vie des bulletins de salaire.

    Le bulletin est le document central de la paie.
    Une fois PAYE, il génère automatiquement une écriture comptable OHADA.
    """

    queryset = BulletinSalaire.objects.all()
    permission_classes = [CanManagePayroll]
    filterset_fields = ["personnel", "statut", "mois", "annee"]
    search_fields = ["personnel__nom", "personnel__postnom", "personnel__prenom"]
    ordering_fields = ["annee", "mois", "salaire_net", "created_at"]
    ordering = ["-annee", "-mois"]

    def get_serializer_class(self):
        if self.action == "list":
            return BulletinSalaireListSerializer
        return BulletinSalaireSerializer

    def get_queryset(self):
        return self.queryset.select_related("personnel__user", "contrat", "paiement", "created_by")

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def list(self, request, *args, **kwargs):
        """Liste les bulletins (filtrables par personnel, statut, mois, annee)."""
        cache_key_args = {"user_id": getattr(request.user, "id", None), "params": dict(request.query_params)}
        cached = CacheManager.get("paie_bulletins_list", **cache_key_args)
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

        CacheManager.set("paie_bulletins_list", data, **cache_key_args, timeout=300)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        """Détail complet d'un bulletin de salaire."""
        serializer = BulletinSalaireSerializer(self.get_object())
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Génère un bulletin de salaire pour un personnel.

        Body obligatoires : contrat, personnel, mois, annee
        Body optionnels   : nb_jours_absence, nb_heures_supplementaires,
                            prime_motivation, autres_primes, note_primes,
                            autres_retenues, note_retenues
        """
        serializer = BulletinSalaireSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        try:
            bulletin = BulletinSalaireService.generer_bulletin(
                contrat=vd["contrat"],
                mois=vd["mois"],
                annee=vd["annee"],
                user=request.user,
                nb_jours_absence=vd.get("nb_jours_absence", 0),
                nb_heures_supplementaires=vd.get("nb_heures_supplementaires", Decimal("0")),
                prime_motivation=vd.get("prime_motivation"),
                autres_primes=vd.get("autres_primes", Decimal("0")),
                note_primes=vd.get("note_primes"),
                autres_retenues=vd.get("autres_retenues", Decimal("0")),
                note_retenues=vd.get("note_retenues"),
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        CacheManager.invalidate_pattern("paie_bulletins_list:*")
        AuditLog.log(
            user=request.user, action="create",
            description=(
                f"Bulletin généré : {bulletin.personnel} {bulletin.mois:02d}/{bulletin.annee} "
                f"— Net : {bulletin.salaire_net}"
            ),
            content_object=bulletin, request=request,
        )
        return Response(BulletinSalaireSerializer(bulletin).data, status=status.HTTP_201_CREATED)

    # ── Actions métier ────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        """
        Valide un bulletin BROUILLON.
        Un bulletin validé peut ensuite être payé.
        """
        bulletin = self.get_object()
        try:
            bulletin = BulletinSalaireService.valider_bulletin(bulletin, request.user)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        CacheManager.invalidate_pattern("paie_bulletins_list:*")
        AuditLog.log(user=request.user, action="update",
                     description=f"Bulletin validé : {bulletin}", content_object=bulletin, request=request)

        return Response(BulletinSalaireSerializer(bulletin).data)

    @action(detail=True, methods=["post"])
    def payer(self, request, pk=None):
        """
        Déclenche le paiement d'un bulletin VALIDE.

        - Crée un PaiementSalaire lié au bulletin
        - Comptabilise en OHADA (débit charges / crédit trésorerie)
        - Met le bulletin en statut PAYE

        Body : { mode: "CASH"|"BANK"|"MOBILE", annee_academique: <id>, note: "..." }
        """
        bulletin = self.get_object()

        mode = request.data.get("mode", "CASH")
        note = request.data.get("note")
        annee_academique_id = request.data.get("annee_academique")

        if mode not in ("CASH", "BANK", "MOBILE"):
            return Response(
                {"error": "Mode invalide. Valeurs acceptées : CASH, BANK, MOBILE"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        annee_academique = None
        if annee_academique_id:
            from core.models import AnneeAcademique
            try:
                annee_academique = AnneeAcademique.objects.get(pk=annee_academique_id)
            except AnneeAcademique.DoesNotExist:
                return Response({"error": "Année académique introuvable"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bulletin, paiement = BulletinSalaireService.payer_bulletin(
                bulletin=bulletin,
                mode=mode,
                user=request.user,
                note=note,
                annee_academique=annee_academique,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        CacheManager.invalidate_pattern("paie_bulletins_list:*")
        CacheManager.invalidate_pattern("paie_salaires_list:*")

        AuditLog.log(
            user=request.user, action="update",
            description=(
                f"Bulletin payé : {bulletin} — "
                f"Réf : {paiement.reference} — Montant : {paiement.montant}"
            ),
            content_object=bulletin,
            metadata={
                "paiement_id": paiement.id,
                "paiement_reference": paiement.reference,
                "montant": float(paiement.montant),
                "mode": paiement.mode,
            },
            request=request,
        )

        return Response({
            "bulletin": BulletinSalaireSerializer(bulletin).data,
            "paiement": PaiementSalaireSerializer(paiement).data,
            "message": (
                f"Salaire payé avec succès. Référence : {paiement.reference}. "
                "La transaction comptable a été enregistrée automatiquement."
            ),
        })

    @action(detail=False, methods=["get"])
    def by_personnel(self, request):
        """
        Historique des bulletins d'un personnel.
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
            return self.get_paginated_response(BulletinSalaireListSerializer(page, many=True).data)
        return Response(BulletinSalaireListSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"])
    def masse(self, request):
        """
        Génère les bulletins de salaire en masse pour un mois donné.

        Body :
          mois                   : 1-12 (obligatoire)
          annee                  : ex. 2026 (obligatoire)
          nb_jours_absence_defaut: 0 par défaut si non individualisé
          contrats_data          : liste optionnelle pour personnaliser par contrat
            [ { contrat_id, nb_jours_absence, nb_heures_supplementaires, ... }, ... ]
          Si contrats_data absent → génération pour TOUS les contrats actifs.
        """
        mois = request.data.get("mois")
        annee = request.data.get("annee")

        if not mois or not annee:
            return Response({"error": "mois et annee sont obligatoires"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mois = int(mois)
            annee = int(annee)
            if not (1 <= mois <= 12):
                raise ValueError("mois invalide")
        except (ValueError, TypeError):
            return Response({"error": "mois (1-12) et annee doivent être des entiers valides"}, status=status.HTTP_400_BAD_REQUEST)

        contrats_data_input = request.data.get("contrats_data", [])
        nb_jours_defaut = int(request.data.get("nb_jours_absence_defaut", 0))

        if contrats_data_input:
            contrats_data = []
            for item in contrats_data_input:
                try:
                    contrat = ContratEmploye.objects.get(pk=item["contrat_id"], statut="ACTIF")
                    contrats_data.append({
                        "contrat": contrat,
                        "nb_jours_absence": item.get("nb_jours_absence", nb_jours_defaut),
                        "nb_heures_supplementaires": Decimal(str(item.get("nb_heures_supplementaires", "0"))),
                        "prime_motivation": Decimal(str(item["prime_motivation"])) if "prime_motivation" in item else None,
                        "autres_primes": Decimal(str(item.get("autres_primes", "0"))),
                        "note_primes": item.get("note_primes"),
                        "autres_retenues": Decimal(str(item.get("autres_retenues", "0"))),
                        "note_retenues": item.get("note_retenues"),
                    })
                except ContratEmploye.DoesNotExist:
                    pass
        else:
            contrats_data = [
                {
                    "contrat": c,
                    "nb_jours_absence": nb_jours_defaut,
                    "nb_heures_supplementaires": Decimal("0"),
                }
                for c in ContratEmploye.objects.filter(statut="ACTIF").select_related("personnel")
            ]

        if not contrats_data:
            return Response({"error": "Aucun contrat actif trouvé"}, status=status.HTTP_400_BAD_REQUEST)

        results = BulletinSalaireService.generer_bulletins_masse(
            contrats_data=contrats_data, mois=mois, annee=annee, user=request.user
        )
        CacheManager.invalidate_pattern("paie_bulletins_list:*")

        AuditLog.log(
            user=request.user, action="create",
            description=(
                f"Génération bulletins masse {mois:02d}/{annee} — "
                f"{len(results['created'])} créés, {len(results['skipped'])} ignorés, "
                f"{len(results['errors'])} erreurs"
            ),
            metadata=results, request=request,
        )
        return Response(results, status=status.HTTP_201_CREATED)
