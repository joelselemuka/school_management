"""
ViewSets pour l'audit et la traçabilité.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from common.models import AuditLog, Document
from common.permissions import IsStaffOrDirector
from rest_framework.permissions import IsAuthenticated
from common.mixins import AuditLogFilterMixin, RoleBasedQuerysetMixin


class AuditLogViewSet(AuditLogFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour consulter les logs d'audit.
    
    Filtrage par rôle:
    - Admin/Director: tous les logs
    - Staff: logs de leur équipe
    - Autres: leurs propres actions uniquement
    
    Actions:
    - list: Liste tous les logs (admin seulement)
    - retrieve: Détails d'un log
    - by_user: Logs d'un utilisateur
    - by_model: Logs d'un type de modèle
    - by_object: Logs d'un objet spécifique
    - recent: Logs récents
    - search: Recherche avancée
    """
    
    queryset = AuditLog.objects.all()
    permission_classes = [IsStaffOrDirector]
    filterset_fields = ['user', 'action', 'status']
    search_fields = ['description', 'ip_address']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
    
    def get_serializer_class(self):
        # Importer dynamiquement pour éviter les importations circulaires
        from common.serializers.audit_serializers import AuditLogSerializer
        return AuditLogSerializer
    
    def get_queryset(self):
        # Le filtrage par rôle est fait automatiquement par AuditLogFilterMixin
        queryset = super().get_queryset()
        return queryset.select_related('user', 'content_type')
    
    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Logs d'un utilisateur spécifique."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id requis'}, status=400)
        
        logs = self.get_queryset().filter(user_id=user_id)
        
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_model(self, request):
        """Logs d'un type de modèle."""
        model_name = request.query_params.get('model')
        app_label = request.query_params.get('app')
        
        if not model_name or not app_label:
            return Response(
                {'error': 'model et app requis'},
                status=400
            )
        
        try:
            content_type = ContentType.objects.get(
                app_label=app_label,
                model=model_name.lower()
            )
            logs = self.get_queryset().filter(content_type=content_type)
            
            page = self.paginate_queryset(logs)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(logs, many=True)
            return Response(serializer.data)
            
        except ContentType.DoesNotExist:
            return Response(
                {'error': 'Type de modèle introuvable'},
                status=404
            )
    
    @action(detail=False, methods=['get'])
    def by_object(self, request):
        """Logs d'un objet spécifique."""
        model_name = request.query_params.get('model')
        app_label = request.query_params.get('app')
        object_id = request.query_params.get('object_id')
        
        if not all([model_name, app_label, object_id]):
            return Response(
                {'error': 'model, app et object_id requis'},
                status=400
            )
        
        try:
            content_type = ContentType.objects.get(
                app_label=app_label,
                model=model_name.lower()
            )
            logs = self.get_queryset().filter(
                content_type=content_type,
                object_id=object_id
            )
            
            serializer = self.get_serializer(logs, many=True)
            return Response(serializer.data)
            
        except ContentType.DoesNotExist:
            return Response(
                {'error': 'Type de modèle introuvable'},
                status=404
            )
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Logs récents (24h par défaut)."""
        hours = int(request.query_params.get('hours', 24))
        from datetime import timedelta
        
        since = timezone.now() - timedelta(hours=hours)
        logs = self.get_queryset().filter(timestamp__gte=since)
        
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


class DocumentViewSet(RoleBasedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des documents.
    
    Filtrage par rôle:
    - Admin/Staff/Director: tous les documents
    - Autres: documents publics + leurs documents
    
    Actions:
    - list, create, retrieve, update, destroy
    - by_object: Documents d'un objet
    - by_type: Documents par type
    - download: Télécharger un document
    """
    
    queryset = Document.objects.all()
    permission_classes = [IsAuthenticated]  # Pas de restriction particulière
    filterset_fields = ['type_document', 'uploaded_by', 'is_public']
    search_fields = ['nom', 'description']
    ordering = ['-uploaded_at']
    
    def get_serializer_class(self):
        # Importer dynamiquement pour éviter les importations circulaires
        from common.serializers.document_serializers import DocumentSerializer
        return DocumentSerializer
    
    def get_queryset(self):
        return super().get_queryset().select_related('uploaded_by', 'content_type')
    
    def perform_create(self, serializer):
        document = serializer.save(uploaded_by=self.request.user)
        
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Upload document: {document.nom}',
            content_object=document,
            request=self.request
        )
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Documents par type."""
        doc_type = request.query_params.get('type')
        if not doc_type:
            return Response({'error': 'type requis'}, status=400)
        
        documents = self.get_queryset().filter(type_document=doc_type)
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Télécharge un document."""
        document = self.get_object()
        
        AuditLog.log(
            user=request.user,
            action='view',
            description=f'Téléchargement document: {document.nom}',
            content_object=document,
            request=request
        )
        
        return Response({
            'url': document.file_url,
            'nom': document.nom,
            'taille': document.file_size
        })
