"""Serializers pour l'audit et la traçabilité."""

from rest_framework import serializers
from common.models import AuditLog, Document


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer pour les logs d'audit."""
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'username', 'action', 'description', 
            'content_type', 'object_id', 'object_repr', 'timestamp',
            'ip_address', 'user_agent', 'status'
        ]
        read_only_fields = ['id', 'username', 'timestamp']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer pour les documents."""
    
    class Meta:
        model = Document
        fields = [
            'id', 'nom', 'description', 'type_document', 'file_url', 
            'file_size', 'uploaded_by', 'uploaded_by_full_name', 
            'uploaded_at', 'is_public', 'content_type', 'object_id'
        ]
        read_only_fields = ['id', 'uploaded_by_full_name', 'uploaded_at', 'file_size']