"""
ViewSets pour la gestion des examens et des salles.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Prefetch

from academics.models import Salle, SessionExamen, PlanificationExamen, RepartitionExamen, Evaluation
from academics.serializers.exam_serializers import (
    SalleSerializer, SalleListSerializer,
    SessionExamenSerializer,
    PlanificationExamenSerializer, PlanificationExamenListSerializer,
    RepartitionExamenSerializer, RepartitionExamenListSerializer,
    ExamDistributionRequestSerializer, ExamDistributionResponseSerializer,
    PresenceMarkerSerializer
)
from academics.services.exam_distribution_service import ExamDistributionService
from common.models import AuditLog
from common.year_filter_mixin import AcademicYearFilterMixin


class SalleViewSet(AcademicYearFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des salles.
    
    Actions:
    - list: Liste toutes les salles
    - create: Crée une nouvelle salle
    - retrieve: Détails d'une salle
    - update/partial_update: Modifie une salle
    - destroy: Supprime (soft delete) une salle
    - disponibles: Liste les salles disponibles
    - by_type: Liste les salles par type
    """
    
    enable_year_filter = False  # Les salles ne sont pas liées à une année académique
    permission_classes = [IsAuthenticated]
    filterset_fields = ['type_salle', 'est_disponible', 'actif']
    search_fields = ['code', 'nom', 'batiment']
    ordering_fields = ['code', 'nom', 'capacite']
    ordering = ['code']
    
    def get_queryset(self):
        queryset = Salle.objects.all()
        
        # Filtre par capacité minimale
        min_capacite = self.request.query_params.get('min_capacite', None)
        if min_capacite:
            queryset = queryset.filter(capacite__gte=int(min_capacite))
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SalleListSerializer
        return SalleSerializer
    
    def perform_create(self, serializer):
        salle = serializer.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Création de la salle {salle.code}',
            content_object=salle,
            request=self.request
        )
    
    def perform_update(self, serializer):
        salle = serializer.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='update',
            description=f'Modification de la salle {salle.code}',
            content_object=salle,
            request=self.request
        )
    
    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        """Liste les salles disponibles."""
        salles = self.get_queryset().filter(est_disponible=True, actif=True)
        serializer = SalleListSerializer(salles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Liste les salles groupées par type."""
        type_salle = request.query_params.get('type', 'examen')
        salles = self.get_queryset().filter(type_salle=type_salle, actif=True)
        serializer = SalleListSerializer(salles, many=True)
        return Response(serializer.data)


class SessionExamenViewSet(AcademicYearFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des sessions d'examen.
    
    Actions:
    - list: Liste toutes les sessions
    - create: Crée une nouvelle session
    - retrieve: Détails d'une session
    - update/partial_update: Modifie une session
    - destroy: Supprime (soft delete) une session
    - by_periode: Sessions par période
    - actives: Sessions actives (en cours ou planifiées)
    """
    
    queryset = SessionExamen.objects.all()
    year_filter_field = 'periode__annee_academique'
    serializer_class = SessionExamenSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['periode', 'type_session', 'statut', 'actif']
    search_fields = ['nom']
    ordering_fields = ['date_debut', 'date_fin', 'nom']
    ordering = ['-date_debut']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('periode').annotate(
            nombre_planifications=Count('planifications', distinct=True)
        )
    
    def perform_create(self, serializer):
        session = serializer.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Création de la session d\'examen {session.nom}',
            content_object=session,
            request=self.request
        )
    
    @action(detail=False, methods=['get'])
    def by_periode(self, request):
        """Liste les sessions d'une période spécifique."""
        periode_id = request.query_params.get('periode_id')
        if not periode_id:
            return Response(
                {'error': 'periode_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sessions = self.get_queryset().filter(periode_id=periode_id)
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def actives(self, request):
        """Liste les sessions actives (planifiées ou en cours)."""
        sessions = self.get_queryset().filter(
            statut__in=['planifie', 'en_cours'],
            actif=True
        )
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)


class PlanificationExamenViewSet(AcademicYearFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des planifications d'examen.
    
    Actions:
    - list: Liste toutes les planifications
    - create: Crée une nouvelle planification
    - retrieve: Détails d'une planification
    - update/partial_update: Modifie une planification
    - destroy: Supprime (soft delete) une planification
    - by_evaluation: Planifications par évaluation
    - by_salle: Planifications par salle
    - by_date: Planifications par date
    - summary: Résumé d'une planification avec répartitions
    """
    
    year_filter_field = 'session_examen__periode__annee_academique'
    permission_classes = [IsAuthenticated]
    filterset_fields = ['evaluation', 'salle', 'date_examen', 'session_examen', 'actif']
    search_fields = ['evaluation__nom', 'salle__code']
    ordering_fields = ['date_examen', 'heure_debut']
    ordering = ['date_examen', 'heure_debut']
    
    def get_queryset(self):
        queryset = PlanificationExamen.objects.all()
        return queryset.select_related(
            'evaluation__cours',
            'salle',
            'session_examen'
        ).prefetch_related(
            'surveillants',
            'surveillants__user',
            'repartitions'
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PlanificationExamenListSerializer
        return PlanificationExamenSerializer
    
    def perform_create(self, serializer):
        planification = serializer.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Création planification examen: {planification.evaluation.nom} - {planification.salle.code}',
            content_object=planification,
            request=self.request
        )
    
    @action(detail=False, methods=['get'])
    def by_evaluation(self, request):
        """Liste les planifications d'une évaluation."""
        evaluation_id = request.query_params.get('evaluation_id')
        if not evaluation_id:
            return Response(
                {'error': 'evaluation_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        planifications = self.get_queryset().filter(evaluation_id=evaluation_id)
        serializer = self.get_serializer(planifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_salle(self, request):
        """Liste les planifications d'une salle."""
        salle_id = request.query_params.get('salle_id')
        if not salle_id:
            return Response(
                {'error': 'salle_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        planifications = self.get_queryset().filter(salle_id=salle_id)
        serializer = self.get_serializer(planifications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Récupère le résumé complet d'une planification avec la liste des élèves."""
        planification = self.get_object()
        summary = ExamDistributionService.get_distribution_summary(planification)
        return Response(summary)


class RepartitionExamenViewSet(AcademicYearFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des répartitions d'élèves.
    
    Actions:
    - list: Liste toutes les répartitions
    - create: Crée une nouvelle répartition manuelle
    - retrieve: Détails d'une répartition
    - update/partial_update: Modifie une répartition
    - destroy: Supprime (soft delete) une répartition
    - by_planification: Répartitions par planification
    - by_eleve: Répartitions par élève
    - mark_present: Marque un élève présent
    """
    
    year_filter_field = 'planification__session_examen__periode__annee_academique'
    permission_classes = [IsAuthenticated]
    filterset_fields = ['planification', 'eleve', 'est_present', 'actif']
    search_fields = ['eleve__nom', 'eleve__prenom', 'eleve__postnom']
    ordering_fields = ['numero_place', 'eleve__nom']
    ordering = ['planification', 'numero_place']
    
    def get_queryset(self):
        queryset = RepartitionExamen.objects.all()
        return queryset.select_related(
            'planification__salle',
            'planification__evaluation',
            'eleve__user'
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RepartitionExamenListSerializer
        return RepartitionExamenSerializer
    
    @action(detail=False, methods=['get'])
    def by_planification(self, request):
        """Liste les répartitions d'une planification."""
        planification_id = request.query_params.get('planification_id')
        if not planification_id:
            return Response(
                {'error': 'planification_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        repartitions = self.get_queryset().filter(planification_id=planification_id)
        serializer = RepartitionExamenSerializer(repartitions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_eleve(self, request):
        """Liste les répartitions d'un élève."""
        eleve_id = request.query_params.get('eleve_id')
        if not eleve_id:
            return Response(
                {'error': 'eleve_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        repartitions = self.get_queryset().filter(eleve_id=eleve_id)
        serializer = RepartitionExamenSerializer(repartitions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_present(self, request):
        """Marque un élève comme présent à l'examen."""
        serializer = PresenceMarkerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        repartition = ExamDistributionService.mark_student_present(
            repartition_id=serializer.validated_data['repartition_id'],
            heure_arrivee=serializer.validated_data.get('heure_arrivee')
        )
        
        # Audit log
        AuditLog.log(
            user=request.user,
            action='update',
            description=f'Présence marquée pour {repartition.eleve}',
            content_object=repartition,
            request=request
        )
        
        result_serializer = RepartitionExamenSerializer(repartition)
        return Response(result_serializer.data)


class ExamDistributionViewSet(viewsets.ViewSet):
    """
    ViewSet pour la génération automatique de répartitions d'examen.
    
    Actions:
    - generate: Génère automatiquement la répartition des élèves
    - validate: Valide qu'une répartition est possible
    """
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Génère automatiquement la répartition des élèves dans les salles.
        
        Body:
        {
            "evaluation_id": 123,
            "salle_ids": [1, 2, 3],
            "max_students_per_class_per_room": 5,
            "spacing_strategy": "alternate",
            "clear_existing": true
        }
        """
        serializer = ExamDistributionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Récupérer l'évaluation et les salles
            evaluation = Evaluation.objects.get(id=serializer.validated_data['evaluation_id'])
            salles = Salle.objects.filter(
                id__in=serializer.validated_data['salle_ids'],
                est_disponible=True,
                actif=True
            )
            
            # Générer la répartition
            result = ExamDistributionService.generate_distribution(
                evaluation=evaluation,
                salles=salles,
                max_students_per_class_per_room=serializer.validated_data['max_students_per_class_per_room'],
                spacing_strategy=serializer.validated_data['spacing_strategy'],
                clear_existing=serializer.validated_data['clear_existing']
            )
            
            # Audit log
            AuditLog.log(
                user=request.user,
                action='create',
                description=f'Génération automatique répartition examen: {evaluation.nom}',
                content_object=evaluation,
                metadata={
                    'total_students': result['total_students'],
                    'total_rooms': result['total_rooms'],
                    'strategy': serializer.validated_data['spacing_strategy']
                },
                request=request
            )
            
            response_data = {
                'total_students': result['total_students'],
                'total_rooms': result['total_rooms'],
                'summary': result['summary'],
                'message': f'Répartition générée avec succès: {result["total_students"]} élèves dans {result["total_rooms"]} salles'
            }
            
            response_serializer = ExamDistributionResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la génération: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """
        Valide qu'une répartition est possible avant de la générer.
        
        Body:
        {
            "evaluation_id": 123,
            "salle_ids": [1, 2, 3]
        }
        """
        evaluation_id = request.data.get('evaluation_id')
        salle_ids = request.data.get('salle_ids', [])
        
        if not evaluation_id or not salle_ids:
            return Response(
                {'error': 'evaluation_id et salle_ids requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            evaluation = Evaluation.objects.get(id=evaluation_id)
            salles = Salle.objects.filter(
                id__in=salle_ids,
                est_disponible=True,
                actif=True
            )
            
            result = ExamDistributionService.validate_distribution(evaluation, salles)
            return Response(result)
            
        except Evaluation.DoesNotExist:
            return Response(
                {'error': 'Évaluation introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
