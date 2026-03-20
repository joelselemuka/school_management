"""
Routing WebSocket pour Django Channels.
"""

from django.urls import re_path
from communication.consumers import ChatConsumer, NotificationConsumer

websocket_urlpatterns = [
    # WebSocket pour le chat en temps réel
    re_path(r'ws/chat/(?P<room_id>\w+)/$', ChatConsumer.as_asgi()),
    
    # WebSocket pour les notifications personnelles
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
]
