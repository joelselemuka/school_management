"""
Views pour la gestion des événements et actualités.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Q, Count

from events.models import Event, Actualite, InscriptionEvenement
from events.serializers import (
    EventSerializer, EventListSerializer, EventPublicSerializer,
    ActualiteSerializer, ActualiteListSerializer, ActualitePubliqueSerializer,
    InscriptionEvenementSerializer
)
from common.permissions import IsStaffOrDirector
from common.models import AuditLog


class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des événements.
    
    Actions disponibles:
    - list: Liste tous les événements
    - create: Créer un nouvel événement
    - retrieve: Détails d'un événement
    - update: Mettre à jour un événement
    - destroy: Supprimer un événement
    - publics: Liste des événements publics (sans authentification)
    - a_venir: Événements à venir
    - passes: Événements passés
    - inscrire: S'inscrire à un événement
    - mes_inscriptions: Mes inscriptions
    """
    
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filterset_fields = ['type_evenement', 'statut', 'annee_academique']
    search_fields = ['titre', 'description', 'lieu']
    ordering = ['-date_debut']
    
    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action in ['publics', 'a_venir']:
            return [AllowAny()]
        elif self.action in ['list', 'retrieve', 'mes_inscriptions']:
            return [IsAuthenticated()]
        else:
            return [IsStaffOrDirector()]
    
    def get_serializer_class(self):
        """Serializer selon l'action."""
        if self.action == 'list':
            return EventListSerializer
        elif self.action == 'publics':
            return EventPublicSerializer
        return EventSerializer
    
    def get_queryset(self):
        """Filtrage selon les rôles."""
        queryset = super().get_queryset().select_related(
            'organisateur',
            'annee_academique'
        ).annotate(
            nombre_inscrits=Count(
                'inscriptions',
                filter=Q(inscriptions__statut='confirme')
            )
        )
        
        # Pour les actions publiques, filtrer les événements publics
        if self.action in ['publics', 'a_venir']:
            queryset = queryset.filter(est_public=True)
        
        return queryset
    
    def perform_create(self, serializer):
        """Créer un événement."""
        event = serializer.save(organisateur=self.request.user)
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Création événement: {event.titre}',
            content_object=event,
            request=self.request
        )
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def publics(self, request):
        """Liste des événements publics (sans authentification requise)."""
        events = self.get_queryset().filter(
            est_public=True,
            statut__in=['planifie', 'en_cours']
        )
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def a_venir(self, request):
        """Liste des événements à venir."""
        events = self.get_queryset().filter(
            date_debut__gte=timezone.now(),
            statut='planifie'
        )
        serializer = EventListSerializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def passes(self, request):
        """Liste des événements passés."""
        events = self.get_queryset().filter(
            Q(date_fin__lt=timezone.now()) | Q(date_debut__lt=timezone.now(), date_fin__isnull=True),
            statut='termine'
        )
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = EventListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = EventListSerializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def inscrire(self, request, pk=None):
        """S'inscrire à un événement."""
        event = self.get_object()
        
        # Vérifications
        if not event.inscription_requise:
            return Response(
                {'error': "Cet événement ne requiert pas d'inscription."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if event.est_passe:
            return Response(
                {'error': "Impossible de s'inscrire à un événement passé."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer l'inscription
        inscription, created = InscriptionEvenement.objects.get_or_create(
            evenement=event,
            participant=request.user,
            defaults={
                'nombre_accompagnants': request.data.get('nombre_accompagnants', 0),
                'commentaire': request.data.get('commentaire', '')
            }
        )
        
        if not created:
            return Response(
                {'error': "Vous êtes déjà inscrit à cet événement."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = InscriptionEvenementSerializer(inscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def mes_inscriptions(self, request):
        """Liste de mes inscriptions."""
        inscriptions = InscriptionEvenement.objects.filter(
            participant=request.user
        ).select_related('evenement', 'participant')
        serializer = InscriptionEvenementSerializer(inscriptions, many=True)
        return Response(serializer.data)


class ActualiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des actualités.
    
    Actions disponibles:
    - list: Liste toutes les actualités
    - create: Créer une nouvelle actualité
    - retrieve: Détails d'une actualité
    - update: Mettre à jour une actualité
    - destroy: Supprimer une actualité
    - publiques: Actualités publiées (sans authentification)
    - publier: Publier une actualité
    - archiver: Archiver une actualité
    - alertes: Liste des alertes actives
    """
    
    queryset = Actualite.objects.all()
    serializer_class = ActualiteSerializer
    filterset_fields = ['categorie', 'statut', 'annee_academique', 'est_une_alerte', 'est_epingle']
    search_fields = ['titre', 'sous_titre', 'contenu', 'tags']
    ordering = ['-est_epingle', '-date_publication', '-created_at']
    
    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action in ['publiques', 'alertes']:
            return [AllowAny()]
        elif self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        else:
            return [IsStaffOrDirector()]
    
    def get_serializer_class(self):
        """Serializer selon l'action."""
        if self.action == 'list':
            return ActualiteListSerializer
        elif self.action == 'publiques':
            return ActualitePubliqueSerializer
        return ActualiteSerializer
    
    def get_queryset(self):
        """Filtrage selon les rôles."""
        queryset = super().get_queryset().select_related('auteur', 'annee_academique')
        
        # Pour les actions publiques, filtrer les actualités publiées
        if self.action in ['publiques', 'alertes']:
            queryset = queryset.filter(statut='publie')
        
        return queryset
    
    def perform_create(self, serializer):
        """Créer une actualité."""
        actualite = serializer.save(auteur=self.request.user)
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Création actualité: {actualite.titre}',
            content_object=actualite,
            request=self.request
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Récupérer une actualité et incrémenter le compteur de vues."""
        instance = self.get_object()
        instance.incrementer_vues()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def publiques(self, request):
        """Liste des actualités publiées (sans authentification requise)."""
        actualites = self.get_queryset().filter(
            statut='publie',
            date_publication__lte=timezone.now()
        ).filter(
            Q(date_expiration__isnull=True) | Q(date_expiration__gte=timezone.now())
        )
        
        page = self.paginate_queryset(actualites)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(actualites, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def publier(self, request, pk=None):
        """Publier une actualité."""
        actualite = self.get_object()
        actualite.statut = 'publie'
        if not actualite.date_publication:
            actualite.date_publication = timezone.now()
        actualite.save()
        
        AuditLog.log(
            user=request.user,
            action='update',
            description=f'Publication actualité: {actualite.titre}',
            content_object=actualite,
            request=request
        )
        
        serializer = self.get_serializer(actualite)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def archiver(self, request, pk=None):
        """Archiver une actualité."""
        actualite = self.get_object()
        actualite.statut = 'archive'
        actualite.save()
        
        AuditLog.log(
            user=request.user,
            action='update',
            description=f'Archivage actualité: {actualite.titre}',
            content_object=actualite,
            request=request
        )
        
        serializer = self.get_serializer(actualite)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def alertes(self, request):
        """Liste des alertes actives."""
        alertes = self.get_queryset().filter(
            statut='publie',
            est_une_alerte=True,
            date_publication__lte=timezone.now()
        ).filter(
            Q(date_expiration__isnull=True) | Q(date_expiration__gte=timezone.now())
        )[:5]  # Limiter à 5 alertes
        
        serializer = ActualitePubliqueSerializer(alertes, many=True)
        return Response(serializer.data)


class InscriptionEvenementViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des inscriptions aux événements.
    """
    
    queryset = InscriptionEvenement.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ['evenement', 'statut']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        return InscriptionEvenementSerializer
    
    def get_queryset(self):
        """Filtrage selon les rôles."""
        queryset = super().get_queryset().select_related('evenement', 'participant')
        
        # Les utilisateurs voient seulement leurs inscriptions
        if not self.request.user.is_staff:
            queryset = queryset.filter(participant=self.request.user)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def confirmer(self, request, pk=None):
        """Confirmer une inscription."""
        inscription = self.get_object()
        inscription.statut = 'confirme'
        inscription.save()
        
        serializer = self.get_serializer(inscription)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        """Annuler une inscription."""
        inscription = self.get_object()
        inscription.statut = 'annule'
        inscription.save()
        
        serializer = self.get_serializer(inscription)
        return Response(serializer.data)
