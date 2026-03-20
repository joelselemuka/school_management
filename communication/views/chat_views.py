"""
ViewSets pour la gestion du chat inter-scolaire.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Prefetch, OuterRef, Subquery, DateTimeField, F, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime

from communication.models import ChatRoom, ChatRoomMember, ChatMessage, NotificationPreference
from communication.serializers.chat_serializers import (
    ChatRoomSerializer, ChatRoomListSerializer, ChatRoomCreateSerializer,
    ChatRoomMemberSerializer, AddMemberSerializer,
    ChatMessageSerializer, ChatMessageListSerializer, UpdateMessageSerializer,
    NotificationPreferenceSerializer
)
from common.models import AuditLog


class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des salles de chat.
    
    Actions:
    - list: Liste toutes les rooms de l'utilisateur
    - create: Crée une nouvelle room
    - retrieve: Détails d'une room
    - update/partial_update: Modifie une room
    - destroy: Supprime (soft delete) une room
    - my_rooms: Rooms dont je suis membre
    - by_classe: Rooms d'une classe
    - add_member: Ajouter un membre
    - remove_member: Retirer un membre
    - mark_read: Marquer comme lu
    """
    
    permission_classes = [IsAuthenticated]
    filterset_fields = ['type_room', 'classe', 'actif']
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = ChatRoom.objects.all()
        min_dt = timezone.make_aware(datetime(1970, 1, 1))
        last_read_subquery = (
            ChatRoomMember.objects
            .filter(room=OuterRef("pk"), user=self.request.user)
            .values("last_read_at")[:1]
        )
        queryset = queryset.annotate(
            membres_count=Count("memberships", distinct=True),
            last_read_at=Subquery(last_read_subquery, output_field=DateTimeField()),
            total_messages=Count(
                "messages",
                filter=Q(messages__is_deleted=False),
                distinct=True
            ),
            unread_messages=Count(
                "messages",
                filter=(
                    Q(messages__is_deleted=False)
                    & Q(messages__created_at__gt=Coalesce(F("last_read_at"), Value(min_dt)))
                    & ~Q(messages__sender=self.request.user)
                ),
                distinct=True
            ),
        )

        current_memberships = ChatRoomMember.objects.filter(user=self.request.user)

        return (
            queryset
            .select_related('classe', 'created_by')
            .prefetch_related(
                Prefetch(
                    "memberships",
                    queryset=current_memberships,
                    to_attr="current_user_memberships"
                )
            )
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChatRoomListSerializer
        elif self.action == 'create':
            return ChatRoomCreateSerializer
        return ChatRoomSerializer
    
    def create(self, request, *args, **kwargs):
        """Crée une nouvelle room de chat."""
        serializer = ChatRoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Créer la room
        room_data = {
            'nom': serializer.validated_data['nom'],
            'type_room': serializer.validated_data['type_room'],
            'description': serializer.validated_data.get('description', ''),
            'est_modere': serializer.validated_data.get('est_modere', True),
            'created_by': request.user
        }
        
        if serializer.validated_data.get('classe_id'):
            from academics.models import Classe
            room_data['classe'] = Classe.objects.get(id=serializer.validated_data['classe_id'])
        
        room = ChatRoom.objects.create(**room_data)
        
        # Ajouter le créateur comme admin
        ChatRoomMember.objects.create(
            room=room,
            user=request.user,
            role='admin'
        )
        
        # Ajouter les autres membres
        membre_ids = serializer.validated_data.get('membre_ids', [])
        for user_id in membre_ids:
            if user_id != request.user.id:
                from users.models import User
                user = User.objects.get(id=user_id)
                ChatRoomMember.objects.create(
                    room=room,
                    user=user,
                    role='membre'
                )
        
        # Audit log
        AuditLog.log(
            user=request.user,
            action='create',
            description=f'Création room chat: {room.nom}',
            content_object=room,
            request=request
        )
        
        result_serializer = ChatRoomSerializer(room, context={'request': request})
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def my_rooms(self, request):
        """Liste les rooms dont l'utilisateur est membre."""
        memberships = ChatRoomMember.objects.filter(user=request.user).select_related('room')
        rooms = [m.room for m in memberships if m.room.actif]
        serializer = ChatRoomListSerializer(
            rooms,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_classe(self, request):
        """Liste les rooms d'une classe spécifique."""
        classe_id = request.query_params.get('classe_id')
        if not classe_id:
            return Response(
                {'error': 'classe_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rooms = self.get_queryset().filter(classe_id=classe_id, type_room='classe')
        serializer = ChatRoomSerializer(rooms, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Ajoute un membre à la room."""
        room = self.get_object()
        
        # Vérifier que l'utilisateur est admin ou modérateur
        membership = room.memberships.filter(user=request.user).first()
        if not membership or membership.role not in ['admin', 'moderateur']:
            return Response(
                {'error': 'Permission refusée. Seuls les admins et modérateurs peuvent ajouter des membres'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from users.models import User
        user = User.objects.get(id=serializer.validated_data['user_id'])
        
        # Vérifier si déjà membre
        if room.memberships.filter(user=user).exists():
            return Response(
                {'error': 'Cet utilisateur est déjà membre'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ajouter le membre
        new_member = ChatRoomMember.objects.create(
            room=room,
            user=user,
            role=serializer.validated_data.get('role', 'membre')
        )
        
        # Audit log
        AuditLog.log(
            user=request.user,
            action='update',
            description=f'Ajout membre {user.username} à la room {room.nom}',
            content_object=room,
            request=request
        )
        
        result_serializer = ChatRoomMemberSerializer(new_member)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """Retire un membre de la room."""
        room = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier les permissions
        membership = room.memberships.filter(user=request.user).first()
        if not membership or membership.role != 'admin':
            return Response(
                {'error': 'Permission refusée. Seuls les admins peuvent retirer des membres'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Trouver et supprimer le membre
        target_membership = room.memberships.filter(user_id=user_id).first()
        if not target_membership:
            return Response(
                {'error': 'Membre introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        target_membership.delete()
        
        # Audit log
        AuditLog.log(
            user=request.user,
            action='update',
            description=f'Retrait membre {target_membership.user.username} de la room {room.nom}',
            content_object=room,
            request=request
        )
        
        return Response({'message': 'Membre retiré avec succès'})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Marque tous les messages de la room comme lus."""
        room = self.get_object()
        
        membership = room.memberships.filter(user=request.user).first()
        if not membership:
            return Response(
                {'error': 'Vous n\'êtes pas membre de cette room'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        membership.last_read_at = timezone.now()
        membership.save()
        
        return Response({'message': 'Messages marqués comme lus'})


class ChatMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des messages de chat.
    
    Actions:
    - list: Liste les messages (filtrable par room)
    - create: Envoie un nouveau message
    - retrieve: Détails d'un message
    - update/partial_update: Modifie un message
    - destroy: Supprime (soft delete) un message
    - by_room: Messages d'une room
    - moderate: Modérer un message
    - pending_moderation: Messages en attente de modération
    """
    
    permission_classes = [IsAuthenticated]
    filterset_fields = ['room', 'sender', 'type_message', 'is_moderated', 'is_deleted']
    search_fields = ['content']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = ChatMessage.objects.all()
        
        # Filtrer uniquement les rooms dont l'utilisateur est membre
        user_rooms = ChatRoom.objects.filter(
            memberships__user=self.request.user
        ).values_list('id', flat=True)
        
        queryset = queryset.filter(room_id__in=user_rooms)
        
        return queryset.select_related('room', 'sender', 'moderated_by')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChatMessageListSerializer
        return ChatMessageSerializer
    
    def perform_create(self, serializer):
        message = serializer.save()
        
        # Audit log pour messages importants (fichiers, etc.)
        if message.type_message in ['file', 'image']:
            AuditLog.log(
                user=self.request.user,
                action='create',
                description=f'Envoi {message.type_message} dans {message.room.nom}',
                content_object=message,
                request=self.request
            )
    
    @action(detail=False, methods=['get'])
    def by_room(self, request):
        """Liste les messages d'une room spécifique."""
        room_id = request.query_params.get('room_id')
        if not room_id:
            return Response(
                {'error': 'room_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que l'utilisateur est membre
        try:
            room = ChatRoom.objects.get(id=room_id)
            if not room.memberships.filter(user=request.user).exists():
                return Response(
                    {'error': 'Vous n\'êtes pas membre de cette room'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': 'Room introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Récupérer les messages
        messages = self.get_queryset().filter(
            room_id=room_id,
            is_deleted=False
        ).order_by('-created_at')
        
        # Pagination
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = ChatMessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def moderate(self, request, pk=None):
        """Modère un message (approuver ou rejeter)."""
        message = self.get_object()
        
        # Vérifier que l'utilisateur est modérateur ou admin
        membership = message.room.memberships.filter(user=request.user).first()
        if not membership or membership.role not in ['admin', 'moderateur']:
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UpdateMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if 'is_moderated' in serializer.validated_data:
            message.is_moderated = serializer.validated_data['is_moderated']
            message.moderated_by = request.user
            message.save()
            
            # Audit log
            AuditLog.log(
                user=request.user,
                action='update',
                description=f'Modération message: {"approuvé" if message.is_moderated else "rejeté"}',
                content_object=message,
                request=request
            )
        
        result_serializer = ChatMessageSerializer(message)
        return Response(result_serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_moderation(self, request):
        """Liste les messages en attente de modération."""
        # Récupérer les rooms où l'utilisateur est modérateur ou admin
        moderated_rooms = ChatRoom.objects.filter(
            memberships__user=request.user,
            memberships__role__in=['admin', 'moderateur'],
            est_modere=True
        ).values_list('id', flat=True)
        
        messages = self.get_queryset().filter(
            room_id__in=moderated_rooms,
            is_moderated=False,
            is_deleted=False
        ).order_by('-created_at')
        
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    def perform_destroy(self, instance):
        """Soft delete du message."""
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            action='delete',
            description=f'Suppression message dans {instance.room.nom}',
            content_object=instance,
            request=self.request
        )


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des préférences de notification.
    
    Actions:
    - list: Liste les préférences (admin uniquement)
    - retrieve: Détails des préférences
    - update/partial_update: Modifie les préférences
    - my_preferences: Mes préférences
    """
    
    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Les utilisateurs ne voient que leurs propres préférences
        if self.request.user.is_staff:
            return NotificationPreference.objects.all()
        return NotificationPreference.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def my_preferences(self, request):
        """Récupère ou met à jour les préférences de l'utilisateur connecté."""
        
        # Créer les préférences si elles n'existent pas
        prefs, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        if request.method == 'GET':
            serializer = NotificationPreferenceSerializer(prefs)
            return Response(serializer.data)
        
        # PUT ou PATCH
        partial = request.method == 'PATCH'
        serializer = NotificationPreferenceSerializer(
            prefs,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Audit log
        AuditLog.log(
            user=request.user,
            action='update',
            description='Modification préférences de notification',
            content_object=prefs,
            request=request
        )
        
        return Response(serializer.data)
