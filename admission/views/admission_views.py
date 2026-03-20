"""
ViewSets pour la gestion des admissions et inscriptions.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from admission.models import AdmissionApplication, Inscription, AdmissionGuardian
from admission.serializers.admission_serializers import AdmissionApplicationSerializer
from admission.serializers.inscription_serializers import BureauInscriptionSerializer, InscriptionSerializer
from admission.services.admission_service import AdmissionService
from admission.services.inscription_service import InscriptionService
from academics.models import Classe
from core.models import AnneeAcademique
from common.cache_utils import CacheManager
from common.models import AuditLog
from common.permissions import CanManageAdmissions
from common.mixins import AdmissionDataFilterMixin


class AdmissionApplicationViewSet(AdmissionDataFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des demandes d'admission.
    
    Filtrage par rôle:
    - Admin/Staff/Director/Secretary: toutes les demandes
    - Parent: leurs propres demandes
    
    Actions:
    - list: Liste toutes les demandes
    - create: Crée une nouvelle demande (inscription en ligne)
    - retrieve: Détails d'une demande
    - update/partial_update: Modifie une demande
    - approve: Valider une demande
    - reject: Rejeter une demande
    - pending: Demandes en attente
    - by_classe: Demandes par classe
    - statistics: Statistiques
    """
    
    queryset = AdmissionApplication.objects.all()
    serializer_class = AdmissionApplicationSerializer
    permission_classes = [CanManageAdmissions]
    filterset_fields = ['status', 'classe_souhaitee', 'annee_academique']
    search_fields = ['eleve_nom', 'eleve_postnom', 'eleve_prenom', 'eleve_email']
    ordering_fields = ['created_at', 'validated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related(
            'classe_souhaitee',
            'annee_academique',
            'validated_by'
        ).prefetch_related('guardians')

    def list(self, request, *args, **kwargs):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("admission_applications_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        CacheManager.set("admission_applications_list", response.data, **cache_key_args, timeout=300)
        return response
    
    def perform_create(self, serializer):
        """Crée une demande d'admission (inscription en ligne)."""
        application = serializer.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user if self.request.user.is_authenticated else None,
            action='create',
            description=f'Nouvelle demande d\'admission: {application.eleve_nom} {application.eleve_postnom}',
            content_object=application,
            request=self.request
        )
        CacheManager.invalidate_pattern("admission_applications_list:*")

        # Envoyer notification (via service)
        try:
            from admission.services.admission_notification_service import AdmissionNotificationService
            AdmissionNotificationService.send_application_received(application)
        except Exception:
            pass  # Ne pas bloquer si la notification échoue
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Valide une demande d'admission."""
        application = self.get_object()
        
        if application.status != 'PENDING':
            return Response(
                {'error': 'Seules les demandes en attente peuvent être validées'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Valider via le service
            result = AdmissionService.approve_application(application, request.user)
            
            # Audit log
            AuditLog.log(
                user=request.user,
                action='update',
                description=f'Validation admission: {application.eleve_nom} {application.eleve_postnom}',
                content_object=application,
                metadata={
                    'inscription_id': result.get('inscription_id'),
                    'eleve_id': result.get('eleve_id')
                },
                request=request
            )
            CacheManager.invalidate_pattern("admission_applications_list:*")
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rejette une demande d'admission."""
        application = self.get_object()
        
        if application.status != 'PENDING':
            return Response(
                {'error': 'Seules les demandes en attente peuvent être rejetées'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        motif = request.data.get('motif', '')
        if not motif:
            return Response(
                {'error': 'Le motif de rejet est obligatoire'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        application.status = 'REJECTED'
        application.validated_by = request.user
        application.validated_at = timezone.now()
        application.save()
        CacheManager.invalidate_pattern("admission_applications_list:*")
        
        # Audit log
        AuditLog.log(
            user=request.user,
            action='update',
            description=f'Rejet admission: {application.eleve_nom} {application.eleve_postnom}',
            content_object=application,
            metadata={'motif': motif},
            request=request
        )
        
        # Envoyer notification
        try:
            from admission.services.admission_notification_service import AdmissionNotificationService
            AdmissionNotificationService.send_application_rejected(application, motif)
        except Exception:
            pass
        
        serializer = self.get_serializer(application)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Liste les demandes en attente."""
        applications = self.get_queryset().filter(status='PENDING')
        
        page = self.paginate_queryset(applications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(applications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_classe(self, request):
        """Liste les demandes par classe souhaitée."""
        classe_id = request.query_params.get('classe_id')
        if not classe_id:
            return Response(
                {'error': 'classe_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        applications = self.get_queryset().filter(classe_souhaitee_id=classe_id)

        page = self.paginate_queryset(applications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(applications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques des demandes d'admission."""
        annee_id = request.query_params.get('annee_id')
        
        filters = {}
        if annee_id:
            filters['annee_academique_id'] = annee_id
        
        from django.db.models import Count
        stats = self.get_queryset().filter(**filters).aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='PENDING')),
            approved=Count('id', filter=Q(status='APPROVED')),
            rejected=Count('id', filter=Q(status='REJECTED'))
        )
        
        return Response(stats)


class InscriptionViewSet(AdmissionDataFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des inscriptions.
    
    Filtrage par rôle:
    - Admin/Staff/Director/Secretary: toutes les inscriptions
    - Teacher: inscriptions de leurs classes
    - Parent: inscriptions de leurs enfants
    - Student: leur propre inscription
    
    Actions:
    - list: Liste toutes les inscriptions
    - create: Crée une inscription (bureau)
    - retrieve: Détails d'une inscription
    - update/partial_update: Modifie une inscription
    - by_eleve: Inscriptions d'un élève
    - by_classe: Inscriptions d'une classe
    - transfer: Transférer un élève
    - promote_batch: Promouvoir plusieurs élèves
    - statistics: Statistiques
    """
    
    queryset = Inscription.objects.all()
    serializer_class = InscriptionSerializer
    permission_classes = [CanManageAdmissions]
    filterset_fields = ['eleve', 'classe', 'annee_academique', 'source']
    search_fields = ['eleve__nom', 'eleve__postnom', 'eleve__prenom']
    ordering_fields = ['date_inscription']
    ordering = ['-date_inscription']

    def get_serializer_class(self):
        if self.action == 'create':
            return BureauInscriptionSerializer
        return InscriptionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related(
            'eleve__user',
            'classe',
            'annee_academique',
            'created_by'
        )

    def list(self, request, *args, **kwargs):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("inscriptions_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        CacheManager.set("inscriptions_list", response.data, **cache_key_args, timeout=300)
        return response
    
    def create(self, request, *args, **kwargs):
        """Crée une inscription (au bureau) avec les données complètes de l'élève."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        classe = get_object_or_404(Classe, id=serializer.validated_data["classe"])
        annee = get_object_or_404(AnneeAcademique, id=serializer.validated_data["annee"])

        inscription = InscriptionService.create_inscription_from_data(
            eleve_data=serializer.validated_data["eleve"],
            guardians_data=serializer.validated_data["guardians"],
            classe=classe,
            annee_academique=annee,
            created_by=request.user,
            source="BUREAU",
        )
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Inscription au bureau: {inscription.eleve} → {inscription.classe.nom}',
            content_object=inscription,
            metadata={
                'eleve_id': inscription.eleve.id,
                'classe_id': inscription.classe.id,
                'annee_id': inscription.annee_academique.id
            },
            request=self.request
        )
        CacheManager.invalidate_pattern("inscriptions_list:*")

        read_serializer = InscriptionSerializer(inscription)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        inscription = serializer.save()
        CacheManager.invalidate_pattern("inscriptions_list:*")
        return inscription

    def perform_destroy(self, instance):
        instance.delete()
        CacheManager.invalidate_pattern("inscriptions_list:*")
    
    @action(detail=False, methods=['get'])
    def by_eleve(self, request):
        """Liste les inscriptions d'un élève."""
        eleve_id = request.query_params.get('eleve_id')
        if not eleve_id:
            return Response(
                {'error': 'eleve_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inscriptions = self.get_queryset().filter(eleve_id=eleve_id)

        page = self.paginate_queryset(inscriptions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(inscriptions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_classe(self, request):
        """Liste les inscriptions d'une classe."""
        classe_id = request.query_params.get('classe_id')
        annee_id = request.query_params.get('annee_id')
        
        if not classe_id or not annee_id:
            return Response(
                {'error': 'classe_id et annee_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inscriptions = self.get_queryset().filter(
            classe_id=classe_id,
            annee_academique_id=annee_id
        )
        
        page = self.paginate_queryset(inscriptions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(inscriptions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        """Transfère un élève vers une autre classe."""
        inscription = self.get_object()
        nouvelle_classe_id = request.data.get('nouvelle_classe_id')
        
        if not nouvelle_classe_id:
            return Response(
                {'error': 'nouvelle_classe_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = InscriptionService.transfer_student(
                inscription,
                nouvelle_classe_id,
                request.user
            )
            
            # Audit log
            AuditLog.log(
                user=request.user,
                action='update',
                description=f'Transfert élève: {inscription.eleve} → classe {nouvelle_classe_id}',
                content_object=inscription,
                metadata=result,
                request=request
            )
            
            return Response(result)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def promote_batch(self, request):
        """Promouvoir plusieurs élèves selon les règles."""
        annee_id = request.data.get('annee_id')
        classe_ids = request.data.get('classe_ids', [])
        
        if not annee_id:
            return Response(
                {'error': 'annee_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = InscriptionService.promote_students(
                annee_id,
                classe_ids,
                request.user
            )
            
            # Audit log
            AuditLog.log(
                user=request.user,
                action='create',
                description=f'Promotion automatique année {annee_id}',
                metadata=result,
                request=request
            )
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques des inscriptions."""
        annee_id = request.query_params.get('annee_id')
        
        filters = {}
        if annee_id:
            filters['annee_academique_id'] = annee_id
        
        from django.db.models import Count
        stats = self.get_queryset().filter(**filters).aggregate(
            total=Count('id'),
            online=Count('id', filter=Q(source='ONLINE')),
            bureau=Count('id', filter=Q(source='BUREAU'))
        )
        
        return Response(stats)
