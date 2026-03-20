"""
Serializers pour la gestion du chat inter-scolaire.
"""

from rest_framework import serializers
from communication.models import ChatRoom, ChatRoomMember, ChatMessage, NotificationPreference
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatRoomMemberSerializer(serializers.ModelSerializer):
    """Serializer pour les membres de chat."""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_nom_complet = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoomMember
        fields = [
            'id', 'room', 'user', 'user_username', 'user_nom_complet',
            'role', 'joined_at', 'last_read_at', 'notifications_enabled',
            'unread_count'
        ]
        read_only_fields = ['id', 'joined_at']
    
    def get_user_nom_complet(self, obj):
        user = obj.user
        eleve = getattr(user, "eleve_profile", None)
        if eleve:
            return f"{eleve.nom} {eleve.postnom} {eleve.prenom}"
        personnel = getattr(user, "personnel_profile", None)
        if personnel:
            return f"{personnel.nom} {personnel.postnom} {personnel.prenom}"
        return user.username
    
    def get_unread_count(self, obj):
        """Compte les messages non lus."""
        if not obj.last_read_at:
            return obj.room.messages.filter(is_deleted=False).count()
        return obj.room.messages.filter(
            created_at__gt=obj.last_read_at,
            is_deleted=False
        ).exclude(sender=obj.user).count()


class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer pour les salles de chat."""
    
    classe_nom = serializers.CharField(source='classe.nom', read_only=True, allow_null=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    membres_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    current_user_membership = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'nom', 'type_room', 'classe', 'classe_nom',
            'description', 'est_modere', 'created_by', 'created_by_username',
            'created_at', 'actif', 'membres_count', 'last_message',
            'current_user_membership'
        ]
        read_only_fields = ['id', 'created_at', 'membres_count']
    
    def get_membres_count(self, obj):
        annotated = getattr(obj, "membres_count", None)
        if annotated is not None:
            return annotated
        return obj.memberships.count()
    
    def get_last_message(self, obj):
        """Récupère le dernier message de la room."""
        last_msg = obj.messages.filter(is_deleted=False).first()
        if last_msg:
            return {
                'id': last_msg.id,
                'sender': last_msg.sender.username,
                'content': last_msg.content[:50],
                'created_at': last_msg.created_at
            }
        return None
    
    def get_current_user_membership(self, obj):
        """Récupère le membership de l'utilisateur courant."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            membership = None
            if hasattr(obj, "current_user_memberships"):
                if obj.current_user_memberships:
                    membership = obj.current_user_memberships[0]
            if membership is None:
                membership = obj.memberships.filter(user=request.user).first()
            if membership:
                return {
                    'id': membership.id,
                    'role': membership.role,
                    'notifications_enabled': membership.notifications_enabled
                }
        return None


class ChatRoomListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes de rooms."""
    
    membres_count = serializers.IntegerField(read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = ['id', 'nom', 'type_room', 'membres_count', 'unread_count']
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if hasattr(obj, "last_read_at") and hasattr(obj, "total_messages") and hasattr(obj, "unread_messages"):
                if obj.last_read_at is None:
                    return obj.total_messages
                return obj.unread_messages

            membership = None
            if hasattr(obj, "current_user_memberships"):
                if obj.current_user_memberships:
                    membership = obj.current_user_memberships[0]
            if membership is None:
                membership = obj.memberships.filter(user=request.user).first()
            if membership:
                if not membership.last_read_at:
                    return obj.messages.filter(is_deleted=False).count()
                return obj.messages.filter(
                    created_at__gt=membership.last_read_at,
                    is_deleted=False
                ).exclude(sender=request.user).count()
        return 0


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer pour les messages de chat."""
    
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_nom_complet = serializers.SerializerMethodField()
    room_nom = serializers.CharField(source='room.nom', read_only=True)
    moderated_by_username = serializers.CharField(
        source='moderated_by.username',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'room', 'room_nom', 'sender', 'sender_username',
            'sender_nom_complet', 'content', 'type_message', 'file_url',
            'is_moderated', 'moderated_by', 'moderated_by_username',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sender', 'is_moderated', 'moderated_by',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at'
        ]
    
    def get_sender_nom_complet(self, obj):
        user = obj.sender
        eleve = getattr(user, "eleve_profile", None)
        if eleve:
            return f"{eleve.nom} {eleve.postnom} {eleve.prenom}"
        personnel = getattr(user, "personnel_profile", None)
        if personnel:
            return f"{personnel.nom} {personnel.postnom} {personnel.prenom}"
        return user.username
    
    def validate(self, data):
        # Vérifier que l'utilisateur est membre de la room
        request = self.context.get('request')
        if request and data.get('room'):
            is_member = data['room'].memberships.filter(user=request.user).exists()
            if not is_member:
                raise serializers.ValidationError({
                    'room': 'Vous n\'êtes pas membre de cette room'
                })
        return data
    
    def create(self, validated_data):
        # Ajouter automatiquement le sender
        request = self.context.get('request')
        validated_data['sender'] = request.user
        
        # Vérifier si la room nécessite modération
        room = validated_data['room']
        if room.est_modere:
            validated_data['is_moderated'] = False
        else:
            validated_data['is_moderated'] = True
        
        return super().create(validated_data)


class ChatMessageListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes de messages."""
    
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'sender_username', 'content', 'type_message',
            'created_at', 'is_deleted'
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer pour les préférences de notification."""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'user_username',
            'email_enabled', 'sms_enabled', 'push_enabled',
            'notes_published', 'absences', 'paiements',
            'annonces', 'chat_messages',
            'digest_frequency', 'quiet_hours_start', 'quiet_hours_end',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'updated_at']
    
    def validate(self, data):
        # Valider les heures silencieuses
        if data.get('quiet_hours_start') and data.get('quiet_hours_end'):
            if data['quiet_hours_end'] <= data['quiet_hours_start']:
                raise serializers.ValidationError({
                    'quiet_hours_end': 'L\'heure de fin doit être après l\'heure de début'
                })
        return data


class ChatRoomCreateSerializer(serializers.Serializer):
    """Serializer pour créer une room de chat."""
    
    nom = serializers.CharField(max_length=200)
    type_room = serializers.ChoiceField(
        choices=['classe', 'groupe', 'general']
    )
    classe_id = serializers.IntegerField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)
    est_modere = serializers.BooleanField(default=True)
    membre_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    
    def validate(self, data):
        # Si type=classe, classe_id est requis
        if data['type_room'] == 'classe' and not data.get('classe_id'):
            raise serializers.ValidationError({
                'classe_id': 'classe_id requis pour type_room=classe'
            })
        
        # Vérifier que la classe existe
        if data.get('classe_id'):
            from academics.models import Classe
            if not Classe.objects.filter(id=data['classe_id']).exists():
                raise serializers.ValidationError({
                    'classe_id': 'Classe introuvable'
                })
        
        return data


class AddMemberSerializer(serializers.Serializer):
    """Serializer pour ajouter un membre à une room."""
    
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(
        choices=['membre', 'moderateur', 'admin'],
        default='membre'
    )
    
    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Utilisateur introuvable")
        return value


class UpdateMessageSerializer(serializers.Serializer):
    """Serializer pour mettre à jour un message."""
    
    content = serializers.CharField(required=False)
    is_moderated = serializers.BooleanField(required=False)
    
    def validate(self, data):
        if not data.get('content') and 'is_moderated' not in data:
            raise serializers.ValidationError(
                "Au moins un champ doit être fourni (content ou is_moderated)"
            )
        return data
