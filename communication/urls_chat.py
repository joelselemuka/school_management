"""
URLs pour les endpoints de chat.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from communication.views.chat_views import (
    ChatRoomViewSet,
    ChatMessageViewSet,
    NotificationPreferenceViewSet
)

router = DefaultRouter()
router.register(r'chat-rooms', ChatRoomViewSet, basename='chat-room')
router.register(r'chat-messages', ChatMessageViewSet, basename='chat-message')
router.register(r'notification-preferences', NotificationPreferenceViewSet, basename='notification-preference')

urlpatterns = [
    path('', include(router.urls)),
]
