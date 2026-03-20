"""
ViewSets pour la gestion financière (Frais, Paiements, Dettes, Factures).
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Sum, Count, Prefetch
from django.utils import timezone

from finance.models import (
    Frais,
    Paiement,
    DetteEleve,
    Facture,
    CompteEleve,
    PaiementAllocation,
)
from finance.serializers.frais_serializers import FraisSerializer
from finance.serializers.paiement_serializer import PaiementSerializer
from finance.serializers.dette_serializer import DetteSerializer

from finance.services.facture_service import FactureService
from finance.services.dette_service import DetteService

from common.cache_utils import CacheManager
from common.models import AuditLog
from common.permissions import CanManageFinance, IsStaffOrDirector
from common.mixins import FinanceDataFilterMixin, RoleBasedQuerysetMixin
from common.year_filter_mixin import AcademicYearFilterMixin
from common.role_services import RoleService
from finance.services.finance_services import FinanceService
from finance.services.paiement_service import PaiementService


class FraisViewSet(AcademicYearFilterMixin, RoleBasedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des frais scolaires.
    
    Filtrage par rôle:
    - Admin/Staff/Director/Accountant: tous les frais
    - Parent: frais de leurs enfants
    - Student: leurs propres frais
    
    Actions:
    - list: Liste tous les frais
    - create: Crée de nouveaux frais
    - retrieve: Détails d'un frais
    - update/partial_update: Modifie un frais
    - destroy: Supprime un frais
    - by_classe: Frais par classe
    - by_annee: Frais par année académique
    - actifs: Frais actifs uniquement
    """
    
    queryset = Frais.objects.all()
    serializer_class = FraisSerializer
    year_filter_field = 'annee_academique'
    permission_classes = [CanManageFinance]
    filterset_fields = ['classe', 'annee_academique', 'obligatoire', 'actif']
    search_fields = ['nom']
    ordering_fields = ['nom', 'montant', 'date_limite', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Frais.objects.all().select_related('classe', 'annee_academique')
        user = self.request.user

        if RoleService.is_admin(user) or RoleService.is_staff(user) or RoleService.is_accountant(user):
            return queryset

        # Parents/élèves: frais de leurs classes uniquement
        if RoleService.is_student(user) or RoleService.is_parent(user):
            from admission.models import Inscription
            if RoleService.is_student(user):
                eleve_ids = [user.eleve_profile.id] if hasattr(user, "eleve_profile") else []
            else:
                eleve_ids = list(
                    user.parent_profile.enfants.values_list("eleve_id", flat=True)
                )

            if not eleve_ids:
                return queryset.none()

            classe_ids = Inscription.objects.filter(
                eleve_id__in=eleve_ids,
                actif=True
            ).values_list("classe_id", flat=True)

            return queryset.filter(classe_id__in=classe_ids)

        return queryset.none()

    def list(self, request, *args, **kwargs):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("frais_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        CacheManager.set("frais_list", response.data, **cache_key_args, timeout=300)
        return response
    
    def perform_create(self, serializer):
        frais = serializer.save()
        CacheManager.invalidate_pattern("frais_list:*")
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Création frais: {frais.nom} - {frais.montant}',
            content_object=frais,
            request=self.request
        )
    
    def perform_update(self, serializer):
        frais = serializer.save()
        CacheManager.invalidate_pattern("frais_list:*")
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='update',
            description=f'Modification frais: {frais.nom}',
            content_object=frais,
            request=self.request
        )

    def perform_destroy(self, instance):
        instance.delete()
        CacheManager.invalidate_pattern("frais_list:*")
    
    @action(detail=False, methods=['get'])
    def by_classe(self, request):
        """Liste les frais d'une classe spécifique."""
        classe_id = request.query_params.get('classe_id')
        if not classe_id:
            return Response(
                {'error': 'classe_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        frais = self.get_queryset().filter(classe_id=classe_id, actif=True)

        page = self.paginate_queryset(frais)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(frais, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_annee(self, request):
        """Liste les frais d'une année académique."""
        annee_id = request.query_params.get('annee_id')
        if not annee_id:
            return Response(
                {'error': 'annee_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        frais = self.get_queryset().filter(annee_academique_id=annee_id, actif=True)

        page = self.paginate_queryset(frais)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(frais, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def actifs(self, request):
        """Liste uniquement les frais actifs."""
        frais = self.get_queryset().filter(actif=True)

        page = self.paginate_queryset(frais)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(frais, many=True)
        return Response(serializer.data)


class PaiementViewSet(FinanceDataFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des paiements.
    
    Filtrage par rôle:
    - Admin/Staff/Director/Accountant: tous les paiements
    - Parent: paiements de leurs enfants
    - Student: leurs propres paiements
    
    Actions:
    - list: Liste tous les paiements
    - create: Enregistre un nouveau paiement
    - retrieve: Détails d'un paiement
    - update/partial_update: Modifie un paiement
    - confirm: Confirme un paiement
    - cancel: Annule un paiement
    - by_eleve: Paiements d'un élève
    - by_statut: Paiements par statut
    - statistics: Statistiques de paiement
    """
    
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer
    permission_classes = [CanManageFinance]
    filterset_fields = ['eleve', 'mode', 'statut', 'created_at']
    search_fields = ['reference', 'transaction_id_externe']
    ordering_fields = ['created_at', 'montant', 'confirmed_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return (
            queryset
            .select_related('eleve__user', 'created_by', 'confirmed_by')
            .prefetch_related('allocations__dette__frais')
        )

    def list(self, request, *args, **kwargs):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("paiements_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        CacheManager.set("paiements_list", response.data, **cache_key_args, timeout=300)
        return response
    
    def perform_create(self, serializer):
        """Crée un paiement et génère la facture."""
        paiement = serializer.save(created_by=self.request.user)
        CacheManager.invalidate_pattern("paiements_list:*")
        
        try:
            # Traiter le paiement via le service
            result = PaiementService.process_payment(paiement)
            
            # Audit log
            AuditLog.log(
                user=self.request.user,
                action='create',
                description=f'Paiement créé: {paiement.reference} - {paiement.montant}',
                content_object=paiement,
                metadata={
                    'eleve_id': paiement.eleve.id,
                    'montant': float(paiement.montant),
                    'mode': paiement.mode
                },
                request=self.request
            )
        except Exception as e:
            # Log l'erreur
            AuditLog.log(
                user=self.request.user,
                action='create',
                description=f'Échec traitement paiement: {paiement.reference}',
                content_object=paiement,
                status='error',
                error_message=str(e),
                request=self.request
            )
            raise
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirme un paiement en attente."""
        paiement = self.get_object()
        
        if paiement.statut != 'PENDING':
            return Response(
                {'error': 'Seuls les paiements en attente peuvent être confirmés'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Confirmer via le service
            result = PaiementService.confirm_payment(paiement, request.user)
            
            # Audit log
            AuditLog.log(
                user=request.user,
                action='update',
                description=f'Paiement confirmé: {paiement.reference}',
                content_object=paiement,
                request=request
            )
            
            serializer = self.get_serializer(result)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annule un paiement."""
        paiement = self.get_object()
        
        if paiement.statut == 'CONFIRMED':
            return Response(
                {'error': 'Un paiement confirmé ne peut pas être annulé'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        paiement.statut = 'CANCELLED'
        paiement.save()
        CacheManager.invalidate_pattern("paiements_list:*")
        
        # Audit log
        AuditLog.log(
            user=request.user,
            action='update',
            description=f'Paiement annulé: {paiement.reference}',
            content_object=paiement,
            request=request
        )
        
        serializer = self.get_serializer(paiement)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_eleve(self, request):
        """Liste les paiements d'un élève."""
        eleve_id = request.query_params.get('eleve_id')
        if not eleve_id:
            return Response(
                {'error': 'eleve_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        paiements = self.get_queryset().filter(eleve_id=eleve_id)
        
        page = self.paginate_queryset(paiements)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(paiements, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_statut(self, request):
        """Liste les paiements par statut."""
        statut = request.query_params.get('statut', 'PENDING')
        paiements = self.get_queryset().filter(statut=statut)

        page = self.paginate_queryset(paiements)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(paiements, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques des paiements."""
        annee_id = request.query_params.get('annee_id')
        
        filters = {}
        if annee_id:
            filters['eleve__inscriptions__annee_academique_id'] = annee_id
        
        stats = self.get_queryset().filter(**filters).aggregate(
            total_paiements=Count('id'),
            total_montant=Sum('montant'),
            total_confirmed=Count('id', filter=Q(statut='CONFIRMED')),
            total_pending=Count('id', filter=Q(statut='PENDING')),
            total_cancelled=Count('id', filter=Q(statut='CANCELLED')),
        )
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export CSV des paiements."""
        import csv
        from django.http import HttpResponse
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="paiements.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Reference', 'Eleve', 'Montant', 'Mode', 'Statut', 'Date'])
        for p in queryset:
            eleve_nom = f"{p.eleve.nom} {p.eleve.prenom}" if p.eleve else "Inconnu"
            writer.writerow([p.reference, eleve_nom, p.montant, p.mode, p.statut, p.created_at.strftime('%Y-%m-%d')])
        return response



class DetteEleveViewSet(FinanceDataFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des dettes élèves.
    
    Filtrage par rôle:
    - Admin/Staff/Director/Accountant: toutes les dettes
    - Parent: dettes de leurs enfants
    - Student: leurs propres dettes
    
    Actions:
    - list: Liste toutes les dettes
    - create: Crée une nouvelle dette (assignation frais à élève)
    - retrieve: Détails d'une dette
    - update/partial_update: Modifie une dette
    - by_eleve: Dettes d'un élève
    - by_statut: Dettes par statut
    - impayes: Liste des impayés
    - generate_for_classe: Génère les dettes pour une classe
    """
    
    queryset = DetteEleve.objects.all()
    serializer_class = DetteSerializer
    permission_classes = [CanManageFinance]
    filterset_fields = ['eleve', 'frais', 'statut']
    ordering_fields = ['created_at', 'montant_du']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('eleve__user', 'frais')

    def perform_create(self, serializer):
        dette = serializer.save()
        CacheManager.invalidate_pattern("dettes_list:*")
        return dette

    def perform_update(self, serializer):
        dette = serializer.save()
        CacheManager.invalidate_pattern("dettes_list:*")
        return dette

    def perform_destroy(self, instance):
        instance.delete()
        CacheManager.invalidate_pattern("dettes_list:*")

    def list(self, request, *args, **kwargs):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("dettes_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        CacheManager.set("dettes_list", response.data, **cache_key_args, timeout=300)
        return response
    
    @action(detail=False, methods=['get'])
    def by_eleve(self, request):
        """Liste les dettes d'un élève."""
        eleve_id = request.query_params.get('eleve_id')
        if not eleve_id:
            return Response(
                {'error': 'eleve_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dettes = self.get_queryset().filter(eleve_id=eleve_id)

        page = self.paginate_queryset(dettes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(dettes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_statut(self, request):
        """Liste les dettes par statut."""
        statut = request.query_params.get('statut', 'IMPAYE')
        dettes = self.get_queryset().filter(statut=statut)

        page = self.paginate_queryset(dettes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(dettes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def impayes(self, request):
        """Liste tous les impayés."""
        dettes = self.get_queryset().filter(
            statut__in=['IMPAYE', 'PARTIEL']
        ).order_by('-montant_du')
        
        page = self.paginate_queryset(dettes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(dettes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate_for_classe(self, request):
        """Génère les dettes pour tous les élèves d'une classe."""
        classe_id = request.data.get('classe_id')
        frais_id = request.data.get('frais_id')
        
        if not classe_id or not frais_id:
            return Response(
                {'error': 'classe_id et frais_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = DetteService.generate_for_classe(classe_id, frais_id)
            
            # Audit log
            AuditLog.log(
                user=request.user,
                action='create',
                description=f'Génération dettes pour classe {classe_id}',
                metadata=result,
                request=request
            )
            CacheManager.invalidate_pattern("dettes_list:*")
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class FactureViewSet(FinanceDataFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour la consultation des factures.
    
    Filtrage par rôle:
    - Admin/Staff/Director/Accountant: toutes les factures
    - Parent: factures de leurs enfants
    - Student: leurs propres factures
    
    Actions:
    - list: Liste toutes les factures
    - retrieve: Détails d'une facture
    - by_eleve: Factures d'un élève
    - download: Télécharge le PDF d'une facture
    """
    
    queryset = Facture.objects.all()
    permission_classes = [CanManageFinance]
    filterset_fields = ['eleve', 'statut', 'date_emission']
    search_fields = ['numero']
    ordering_fields = ['date_emission', 'created_at']
    ordering = ['-date_emission']
    
    def get_serializer_class(self):
        # Importer dynamiquement pour éviter les importations circulaires
        from finance.serializers.facture_serializer import FactureSerializer
        return FactureSerializer
    
    def get_queryset(self):
        # Le filtrage par rôle est fait automatiquement par FinanceDataFilterMixin
        queryset = super().get_queryset()
        return queryset.select_related('eleve__user', 'paiement')

    def list(self, request, *args, **kwargs):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("factures_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        CacheManager.set("factures_list", response.data, **cache_key_args, timeout=300)
        return response
    
    @action(detail=False, methods=['get'])
    def by_eleve(self, request):
        """Liste les factures d'un élève."""
        eleve_id = request.query_params.get('eleve_id')
        if not eleve_id:
            return Response(
                {'error': 'eleve_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        factures = self.get_queryset().filter(eleve_id=eleve_id)

        page = self.paginate_queryset(factures)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(factures, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Télécharge le PDF d'une facture."""
        facture = self.get_object()
        
        if not facture.pdf:
            return Response(
                {'error': 'PDF non disponible'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Audit log
        AuditLog.log(
            user=request.user,
            action='view',
            description=f'Téléchargement facture: {facture.numero}',
            content_object=facture,
            request=request
        )
        
        # Retourner l'URL du fichier
        return Response({
            'url': facture.pdf.url,
            'numero': facture.numero
        })


class CompteEleveViewSet(FinanceDataFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour la consultation des comptes élèves.
    
    Filtrage par rôle:
    - Admin/Staff/Director/Accountant: tous les comptes
    - Parent: comptes de leurs enfants
    - Student: leur propre compte
    
    Actions:
    - list: Liste tous les comptes
    - retrieve: Détails d'un compte
    - by_eleve: Compte d'un élève spécifique
    - solde: Solde d'un élève
    - rapprochement: Rapprochement de compte
    """
    
    queryset = CompteEleve.objects.all()
    permission_classes = [CanManageFinance]
    filterset_fields = ['eleve', 'annee_academique']
    ordering_fields = ['updated_at']
    ordering = ['-updated_at']
    
    def get_serializer_class(self):
        # Importer dynamiquement pour éviter les importations circulaires
        from finance.serializers.compte_serializer import CompteEleveSerializer
        return CompteEleveSerializer
    
    def get_queryset(self):
        # Le filtrage par rôle est fait automatiquement par FinanceDataFilterMixin
        queryset = super().get_queryset().select_related(
            'eleve__user',
            'annee_academique'
        )

        from admission.models import Inscription

        inscriptions_qs = (
            Inscription.objects
            .select_related("classe")
            .order_by("-date_inscription")
        )
        dettes_qs = DetteEleve.objects.select_related("frais")
        paiements_qs = Paiement.objects.select_related("created_by", "confirmed_by")

        return queryset.prefetch_related(
            Prefetch(
                "eleve__inscriptions",
                queryset=inscriptions_qs,
                to_attr="prefetched_inscriptions"
            ),
            Prefetch(
                "eleve__detteeleve_set",
                queryset=dettes_qs,
                to_attr="prefetched_dettes"
            ),
            Prefetch(
                "eleve__paiement_set",
                queryset=paiements_qs,
                to_attr="prefetched_paiements"
            ),
        )

    def list(self, request, *args, **kwargs):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("comptes_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        CacheManager.set("comptes_list", response.data, **cache_key_args, timeout=300)
        return response
    
    @action(detail=False, methods=['get'])
    def by_eleve(self, request):
        """Récupère le compte d'un élève."""
        eleve_id = request.query_params.get('eleve_id')
        annee_id = request.query_params.get('annee_id')
        
        if not eleve_id:
            return Response(
                {'error': 'eleve_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filters = {'eleve_id': eleve_id}
        if annee_id:
            filters['annee_academique_id'] = annee_id
        
        compte = self.get_queryset().filter(**filters).first()
        
        if not compte:
            return Response(
                {'error': 'Compte introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(compte)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def solde(self, request):
        """Récupère le solde d'un élève."""
        eleve_id = request.query_params.get('eleve_id')
        annee_id = request.query_params.get('annee_id')
        
        if not eleve_id or not annee_id:
            return Response(
                {'error': 'eleve_id et annee_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        compte = self.get_queryset().filter(
            eleve_id=eleve_id,
            annee_academique_id=annee_id
        ).first()
        
        if not compte:
            return Response({
                'total_du': 0,
                'total_paye': 0,
                'solde': 0
            })
        
        return Response({
            'total_du': compte.total_du,
            'total_paye': compte.total_paye,
            'solde': compte.solde
        })
    
    @action(detail=False, methods=['post'])
    def rapprochement(self, request):
        """Effectue le rapprochement de compte pour un élève."""
        eleve_id = request.data.get('eleve_id')
        annee_id = request.data.get('annee_id')
        
        if not eleve_id or not annee_id:
            return Response(
                {'error': 'eleve_id et annee_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = FinanceService.rapprochement_compte(eleve_id, annee_id)
            
            # Audit log
            AuditLog.log(
                user=request.user,
                action='update',
                description=f'Rapprochement compte élève {eleve_id}',
                metadata=result,
                request=request
            )
            
            return Response(result)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class FinanceReportViewSet(viewsets.ViewSet):
    """
    ViewSet pour les rapports financiers.
    
    Permissions: Admin, Staff, Director, Accountant uniquement
    
    Actions:
    - rapport_global: Rapport global de la situation financière
    - rapport_par_classe: Rapport par classe
    - impayes_par_eleve: Liste des impayés
    - impayes_par_classe: Liste des élèves insolvables par classe
    """
    
    permission_classes = [IsStaffOrDirector]
    
    @action(detail=False, methods=['get'])
    def rapport_global(self, request):
        """Rapport financier global."""
        annee_id = request.query_params.get('annee_id')
        
        if not annee_id:
            return Response(
                {'error': 'annee_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rapport = FinanceService.generate_global_report(annee_id)
            return Response(rapport)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def rapport_par_classe(self, request):
        """Rapport financier par classe."""
        classe_id = request.query_params.get('classe_id')
        annee_id = request.query_params.get('annee_id')
        
        if not classe_id or not annee_id:
            return Response(
                {'error': 'classe_id et annee_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rapport = FinanceService.generate_class_report(classe_id, annee_id)
            return Response(rapport)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def impayes_par_eleve(self, request):
        """Liste des élèves avec impayés."""
        annee_id = request.query_params.get('annee_id')
        
        filters = {'statut__in': ['IMPAYE', 'PARTIEL']}
        if annee_id:
            filters['frais__annee_academique_id'] = annee_id
        
        dettes = DetteEleve.objects.filter(**filters).select_related(
            'eleve__user', 'frais'
        ).order_by('-montant_du')
        
        # Grouper par élève
        eleves_impayes = {}
        for dette in dettes:
            eleve_id = dette.eleve.id
            if eleve_id not in eleves_impayes:
                eleves_impayes[eleve_id] = {
                    'eleve_id': eleve_id,
                    'nom_complet': f"{dette.eleve.nom} {dette.eleve.postnom} {dette.eleve.prenom}",
                    'matricule': dette.eleve.user.matricule,
                    'total_du': 0,
                    'dettes': []
                }
            
            eleves_impayes[eleve_id]['total_du'] += float(dette.montant_du)
            eleves_impayes[eleve_id]['dettes'].append({
                'frais': dette.frais.nom,
                'montant_du': float(dette.montant_du),
                'statut': dette.statut
            })
        
        results = list(eleves_impayes.values())
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(results, request)
        if page is not None:
            return paginator.get_paginated_response(page)

        return Response(results)

    @action(detail=False, methods=['get'])
    def impayes_par_classe(self, request):
        """Liste des élèves insolvables pour une classe donnée."""
        classe_id = request.query_params.get('classe_id')
        if not classe_id:
            return Response(
                {'error': 'classe_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        annee_id = request.query_params.get('annee_id')

        filters = {
            'statut__in': ['IMPAYE', 'PARTIEL'],
            'frais__classe_id': classe_id
        }
        if annee_id:
            filters['frais__annee_academique_id'] = annee_id

        dettes = DetteEleve.objects.filter(**filters).select_related(
            'eleve__user', 'frais', 'frais__classe'
        ).order_by('-montant_du')

        # Grouper par élève
        eleves_impayes = {}
        for dette in dettes:
            eleve_id = dette.eleve.id
            if eleve_id not in eleves_impayes:
                eleves_impayes[eleve_id] = {
                    'eleve_id': eleve_id,
                    'nom_complet': f"{dette.eleve.nom} {dette.eleve.postnom} {dette.eleve.prenom}",
                    'matricule': dette.eleve.user.matricule,
                    'classe_id': dette.frais.classe_id,
                    'classe_nom': dette.frais.classe.nom,
                    'total_du': 0,
                    'dettes': []
                }

            eleves_impayes[eleve_id]['total_du'] += float(dette.montant_du)
            eleves_impayes[eleve_id]['dettes'].append({
                'frais': dette.frais.nom,
                'montant_du': float(dette.montant_du),
                'statut': dette.statut
            })

        results = list(eleves_impayes.values())
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(results, request)
        if page is not None:
            return paginator.get_paginated_response(page)

        return Response(results)

    @action(detail=False, methods=['get'])
    def rapport_periodique(self, request):
        """Rapport financier par période (mensuel, hebdomadaire)."""
        periode = request.query_params.get('periode', 'mensuel') 
        
        from django.db.models.functions import TruncMonth, TruncWeek
        trunc_func = TruncWeek('created_at') if periode == 'hebdomadaire' else TruncMonth('created_at')
        
        stats = Paiement.objects.filter(statut='CONFIRMED').annotate(
            period=trunc_func
        ).values('period').annotate(
            total_rentrees=Sum('montant'),
            nombre_paiements=Count('id')
        ).order_by('-period')
        
        return Response(stats)
