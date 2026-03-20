"""Serializers pour les documents."""

from rest_framework import serializers
from common.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer pour les documents."""
    
    class Meta:
        model = Document
        fields = [
            'id', 'nom', 'description', 'type_document', 'file_path', 
            'file_size', 'uploaded_by', 'uploaded_at', 'is_public', 
            'content_type', 'object_id'
        ]
        read_only_fields = ['id', 'file_size', 'uploaded_at']
