

from rest_framework import serializers

from communication.models import NotificationPreference, NotificationRecipient

class UserNotificationSerializer(serializers.ModelSerializer):

    titre = serializers.CharField(source="campaign.template.titre")
    message = serializers.CharField(source="campaign.template.message")

    class Meta:
        model = NotificationRecipient
        fields = ["id","titre","message","is_read","read_at"]

class NotificationPreferenceSerializer(serializers.ModelSerializer):

    class Meta:
        model = NotificationPreference
        fields = ["email","web","push"]
