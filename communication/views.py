from django.utils import timezone
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers
from communication.models import NotificationPreference, NotificationUser
from communication.serializers import NotificationPreferenceSerializer


class UserNotificationSerializer(serializers.ModelSerializer):
    """Serializer pour les notifications utilisateur."""
    class Meta:
        model = NotificationUser
        fields = ['id', 'notification', 'user', 'is_read', 'read_at']
        read_only_fields = ['id', 'notification', 'user']

class UserNotificationView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationSerializer

    def get(self, request):
        qs = NotificationUser.objects.filter(
            user=request.user
        ).select_related("notification").order_by("-id")
        serializer = self.get_serializer_class()(qs, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        return UserNotificationSerializer


class MarkNotificationRead(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, pk):
        notif = NotificationUser.objects.get(pk=pk, user=request.user)
        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=["is_read", "read_at"])
        return Response({"detail": "ok"})


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer

    def get(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = self.get_serializer_class()(pref)
        return Response(serializer.data)

    def put(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = self.get_serializer_class()(pref, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_serializer_class(self):
        return NotificationPreferenceSerializer

