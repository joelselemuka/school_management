"""
WebSocket Consumers pour le chat en temps réel.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consumer pour le chat en temps réel.
    
    Format des messages:
    {
        "type": "chat_message",
        "message": "Contenu du message",
        "room_id": 123,
        "sender_id": 456
    }
    """
    
    async def connect(self):
        """Connexion WebSocket."""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        
        # Vérifier si l'utilisateur est authentifié
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Vérifier si l'utilisateur a accès à ce salon
        has_access = await self.check_room_access()
        if not has_access:
            await self.close()
            return
        
        # Rejoindre le groupe du salon
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer un message de connexion
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket."""
        # Envoyer un message de déconnexion
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_leave',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )
        
        # Quitter le groupe du salon
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Réception d'un message du client."""
        data = json.loads(text_data)
        message_type = data.get('type', 'chat_message')
        
        if message_type == 'chat_message':
            message_content = data.get('message', '')
            
            # Sauvegarder le message en base de données
            message = await self.save_message(message_content)
            
            # Envoyer le message à tous les membres du groupe
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message['id'],
                    'message': message_content,
                    'sender_id': self.user.id,
                    'sender_name': self.user.get_full_name(),
                    'timestamp': message['timestamp'],
                }
            )
        
        elif message_type == 'typing':
            # Indicateur de frappe
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_typing': data.get('is_typing', False),
                }
            )
        
        elif message_type == 'mark_read':
            # Marquer les messages comme lus
            message_ids = data.get('message_ids', [])
            await self.mark_messages_read(message_ids)
    
    async def chat_message(self, event):
        """Envoyer un message de chat au WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event['message_id'],
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp'],
        }))
    
    async def user_join(self, event):
        """Notification d'arrivée d'un utilisateur."""
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'user_id': event['user_id'],
            'username': event['username'],
        }))
    
    async def user_leave(self, event):
        """Notification de départ d'un utilisateur."""
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'user_id': event['user_id'],
            'username': event['username'],
        }))
    
    async def typing_indicator(self, event):
        """Indicateur de frappe."""
        # Ne pas envoyer à soi-même
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))
    
    @database_sync_to_async
    def check_room_access(self):
        """Vérifie si l'utilisateur a accès au salon."""
        from communication.models import ChatRoom, ChatRoomMember
        
        try:
            # Vérifier si l'utilisateur est membre du salon
            return ChatRoomMember.objects.filter(
                room_id=self.room_id,
                user=self.user
            ).exists()
        except:
            return False
    
    @database_sync_to_async
    def save_message(self, content):
        """Sauvegarde le message en base de données."""
        from communication.models import ChatMessage
        from django.utils import timezone
        
        message = ChatMessage.objects.create(
            room_id=self.room_id,
            sender=self.user,
            content=content,
        )
        
        return {
            'id': message.id,
            'timestamp': message.sent_at.isoformat(),
        }
    
    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        """Marque les messages comme lus."""
        from communication.models import ChatMessage
        
        ChatMessage.objects.filter(
            id__in=message_ids,
            room_id=self.room_id
        ).exclude(
            sender=self.user
        ).update(read_by=self.user)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumer pour les notifications en temps réel.
    
    Chaque utilisateur a son propre canal de notifications.
    """
    
    async def connect(self):
        """Connexion WebSocket."""
        self.user = self.scope['user']
        
        # Vérifier si l'utilisateur est authentifié
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Canal de notifications personnel
        self.notification_group_name = f'notifications_{self.user.id}'
        
        # Rejoindre le groupe de notifications
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket."""
        await self.channel_layer.group_discard(
            self.notification_group_name,
            self.channel_name
        )
    
    async def notification_message(self, event):
        """Envoyer une notification au WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification_id': event['notification_id'],
            'title': event['title'],
            'message': event['message'],
            'notification_type': event['notification_type'],
            'timestamp': event['timestamp'],
            'data': event.get('data', {}),
        }))
