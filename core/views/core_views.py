"""
ViewSets pour les entités core (configuration, années académiques, périodes).
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count

from core.models import Ecole, AnneeAcademique, Periode, ReglePromotion
from core.serializers.core_serializers import (
    EcoleSerializer, AnneeAcademiqueSerializer, AnneeAcademiqueListSerializer,
    PeriodeSerializer, PeriodeListSerializer, ReglePromotionSerializer
)
from common.models import AuditLog
from common.permissions import IsStaffOrDirector, HasRBACPermission
from common.mixins import RoleBasedQuerysetMixin


class EcoleViewSet(RoleBasedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la configuration de l'école.
    
    Permissions: Admin/Staff/Director uniquement
    
    Actions:
    - list, retrieve, update
    - current: Configuration actuelle
    """
    
    queryset = Ecole.objects.all()
    serializer_class = EcoleSerializer
    permission_classes = [IsStaffOrDirector]
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Récupère la configuration actuelle de l'école."""
        ecole = Ecole.objects.first()
        if not ecole:
            return Response(
                {'error': 'Configuration école non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(ecole)
        return Response(serializer.data)


class AnneeAcademiqueViewSet(RoleBasedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des années académiques.
    
    Permissions: Admin/Staff/Director pour CUD, tous pour lecture
    
    Actions:
    - list, create, retrieve, update, destroy
    - current: Année académique active
    - activate: Activer une année
    - close: Clôturer une année
    - statistics: Statistiques d'une année
    """
    
    queryset = AnneeAcademique.objects.all()
    permission_classes = [HasRBACPermission]
    ordering = ['-date_debut']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AnneeAcademiqueListSerializer
        return AnneeAcademiqueSerializer
    
    def perform_create(self, serializer):
        annee = serializer.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Création année académique: {annee.nom}',
            content_object=annee,
            request=self.request
        )
    
    def perform_update(self, serializer):
        annee = serializer.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='update',
            description=f'Modification année académique: {annee.nom}',
            content_object=annee,
            request=self.request
        )
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Récupère l'année académique active."""
        today = timezone.now().date()
        annee = AnneeAcademique.objects.filter(
            date_debut__lte=today,
            date_fin__gte=today,
            actif=True
        ).first()
        
        if not annee:
            return Response(
                {'error': 'Aucune année académique active'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AnneeAcademiqueSerializer(annee)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Active une année académique."""
        annee = self.get_object()
        
        # Désactiver les autres années
        AnneeAcademique.objects.exclude(id=annee.id).update(actif=False)
        
        # Activer cette année
        annee.actif = True
        annee.save()
        
        # Audit log
        AuditLog.log(
            user=request.user,
            action='update',
            description=f'Activation année académique: {annee.nom}',
            content_object=annee,
            request=request
        )
        
        serializer = self.get_serializer(annee)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Clôture une année académique."""
        annee = self.get_object()
        
        annee.actif = False
        annee.save()
        
        # Audit log
        AuditLog.log(
            user=request.user,
            action='update',
            description=f'Clôture année académique: {annee.nom}',
            content_object=annee,
            request=request
        )
        
        serializer = self.get_serializer(annee)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Statistiques d'une année académique."""
        annee = self.get_object()
        
        from admission.models import Inscription
        from academics.models import Evaluation

        stats = {
            'annee': annee.nom,
            'nombre_inscriptions': Inscription.objects.filter(
                annee_academique=annee
            ).count(),
            'nombre_periodes': annee.periodes.count(),
            'nombre_evaluations': Evaluation.objects.filter(
                periode__annee_academique=annee
            ).count(),
            'est_active': annee.est_active
        }
        
        return Response(stats)


class PeriodeViewSet(RoleBasedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des périodes/trimestres.
    
    Permissions: Admin/Staff/Director pour CUD, tous pour lecture
    
    Actions:
    - list, create, retrieve, update, destroy
    - by_annee: Périodes d'une année
    - current: Période active
    - statistics: Statistiques d'une période
    """
    
    queryset = Periode.objects.all()
    permission_classes = [HasRBACPermission]
    filterset_fields = ['annee_academique', 'actif']
    ordering = ['date_debut']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PeriodeListSerializer
        return PeriodeSerializer
    
    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related('annee_academique')
            .annotate(
                nombre_evaluations=Count('evaluation', distinct=True)
            )
        )
    
    def perform_create(self, serializer):
        periode = serializer.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Création période: {periode.nom}',
            content_object=periode,
            request=self.request
        )
    
    def perform_update(self, serializer):
        periode = serializer.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='update',
            description=f'Modification période: {periode.nom}',
            content_object=periode,
            request=self.request
        )
    
    @action(detail=False, methods=['get'])
    def by_annee(self, request):
        """Liste les périodes d'une année académique."""
        annee_id = request.query_params.get('annee_id')
        if not annee_id:
            return Response(
                {'error': 'annee_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        periodes = self.get_queryset().filter(annee_academique_id=annee_id, actif=True)
        serializer = PeriodeSerializer(periodes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Récupère la période active."""
        today = timezone.now().date()
        periode = Periode.objects.filter(
            date_debut__lte=today,
            date_fin__gte=today,
            actif=True
        ).first()
        
        if not periode:
            return Response(
                {'error': 'Aucune période active'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PeriodeSerializer(periode)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Statistiques d'une période."""
        periode = self.get_object()

        from academics.models import Evaluation, Bulletin

        stats = {
            'periode': periode.nom,
            'annee': periode.annee_academique.nom,
            'nombre_evaluations': Evaluation.objects.filter(
                periode=periode
            ).count(),
            'nombre_bulletins': Bulletin.objects.filter(
                periode=periode
            ).count(),
            'est_active': periode.est_active
        }
        
        return Response(stats)


class ReglePromotionViewSet(RoleBasedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des règles de promotion.
    
    Permissions: Admin/Staff/Director uniquement
    
    Actions:
    - list, create, retrieve, update, destroy
    - by_annee: Règles d'une année
    - by_classe: Règle pour une classe
    """
    
    queryset = ReglePromotion.objects.all()
    serializer_class = ReglePromotionSerializer
    permission_classes = [IsStaffOrDirector]
    filterset_fields = ['annee_academique', 'classe_origine', 'actif']
    ordering = ['classe_origine__nom']
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'annee_academique',
            'classe_origine',
            'classe_destination'
        )
    
    def perform_create(self, serializer):
        regle = serializer.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Création règle promotion: {regle.classe_origine.nom} → {regle.classe_destination.nom}',
            content_object=regle,
            request=self.request
        )
    
    @action(detail=False, methods=['get'])
    def by_annee(self, request):
        """Liste les règles d'une année académique."""
        annee_id = request.query_params.get('annee_id')
        if not annee_id:
            return Response(
                {'error': 'annee_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        regles = self.get_queryset().filter(annee_academique_id=annee_id, actif=True)
        serializer = self.get_serializer(regles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_classe(self, request):
        """Récupère la règle pour une classe."""
        classe_id = request.query_params.get('classe_id')
        annee_id = request.query_params.get('annee_id')
        
        if not classe_id or not annee_id:
            return Response(
                {'error': 'classe_id et annee_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        regle = self.get_queryset().filter(
            classe_origine_id=classe_id,
            annee_academique_id=annee_id,
            actif=True
        ).first()
        
        if not regle:
            return Response(
                {'error': 'Règle de promotion introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(regle)
        return Response(serializer.data)
