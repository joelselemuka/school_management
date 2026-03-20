from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey



class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(actif=True)

class SoftDeleteModel(models.Model):
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = ActiveManager()
    all_objects = models.Manager()
    
    class Meta:
        abstract = True

    def soft_delete(self):
        self.actif = False
        self.deleted_at = timezone.now()
        self.save()

    def delete(self, *args, **kwargs):
        self.soft_delete()


# ============================================================================
# AUDIT LOG - Traçabilité complète
# ============================================================================

class AuditLog(models.Model):
    """
    Journal d'audit pour tracer toutes les actions critiques.
    Rétention: >= 5 ans
    """
    
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('view', 'Consultation'),
        ('export', 'Export'),
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
        ('failed_login', 'Connexion Échouée'),
        ('permission_denied', 'Permission Refusée'),
        ('other', 'Autre'),
    ]
    
    # Qui a fait l'action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="Utilisateur ayant effectué l'action"
    )
    username = models.CharField(
        max_length=150,
        help_text="Username sauvegardé (au cas où l'utilisateur est supprimé)"
    )
    
    # Type d'action
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True
    )
    
    # Sur quel objet (GenericForeignKey pour n'importe quel modèle)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Informations sur l'objet
    object_repr = models.CharField(
        max_length=500,
        blank=True,
        help_text="Représentation textuelle de l'objet"
    )
    model_name = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Nom du modèle (ex: User, Classe, Note)"
    )
    
    # Détails de l'action
    description = models.TextField(
        blank=True,
        help_text="Description de l'action"
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Détails des changements (ancien/nouveau)"
    )
    
    # Métadonnées de la requête
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Adresse IP de l'utilisateur"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User Agent du navigateur"
    )
    request_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Chemin de la requête HTTP"
    )
    request_method = models.CharField(
        max_length=10,
        blank=True,
        help_text="Méthode HTTP (GET, POST, PUT, DELETE)"
    )
    
    # Résultat
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Succès'),
            ('failure', 'Échec'),
            ('error', 'Erreur'),
        ],
        default='success',
        db_index=True
    )
    error_message = models.TextField(
        blank=True,
        help_text="Message d'erreur si échec"
    )
    
    # Timestamp
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    
    # Métadonnées additionnelles
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Données additionnelles"
    )
    
    class Meta:
        app_label = 'core'
        db_table = 'common_auditlog'
        verbose_name = 'Log d\'Audit'
        verbose_name_plural = 'Logs d\'Audit'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['model_name', 'timestamp']),
            models.Index(fields=['status']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.username} - {self.action} - {self.model_name} ({self.timestamp})"
    
    @classmethod
    def log(cls, user, action, description='', content_object=None, 
            changes=None, request=None, status='success', error_message=''):
        """
        Méthode helper pour créer un log d'audit.
        
        Usage:
            AuditLog.log(
                user=request.user,
                action='update',
                description='Modification d\'une note',
                content_object=note_instance,
                changes={'valeur': {'old': 15, 'new': 18}},
                request=request
            )
        """
        # Extraire les infos de la requête
        ip_address = None
        user_agent = ''
        request_path = ''
        request_method = ''
        
        if request:
            ip_address = cls._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            request_path = request.path[:500]
            request_method = request.method
        
        # Informations sur l'objet
        object_repr = ''
        model_name = ''
        content_type_obj = None
        object_id = None
        
        if content_object:
            object_repr = str(content_object)[:500]
            model_name = content_object.__class__.__name__
            content_type_obj = ContentType.objects.get_for_model(content_object)
            object_id = content_object.pk
        
        return cls.objects.create(
            user=user,
            username=user.username if user else 'Anonymous',
            action=action,
            content_type=content_type_obj,
            object_id=object_id,
            object_repr=object_repr,
            model_name=model_name,
            description=description,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            request_method=request_method,
            status=status,
            error_message=error_message
        )
    
    @staticmethod
    def _get_client_ip(request):
        """Extrait l'IP du client de la requête."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class Document(models.Model):
    """
    Métadonnées pour les documents stockés sur S3/MinIO.
    """
    
    TYPE_CHOICES = [
        ('bulletin', 'Bulletin'),
        ('facture', 'Facture'),
        ('recu', 'Reçu'),
        ('certificat', 'Certificat'),
        ('rapport', 'Rapport'),
        ('photo', 'Photo'),
        ('autre', 'Autre'),
    ]
    
    nom = models.CharField(max_length=255)
    type_document = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        db_index=True
    )
    description = models.TextField(blank=True)
    
    # Lien vers l'objet associé
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Informations du fichier
    file_path = models.CharField(
        max_length=500,
        help_text="Chemin du fichier dans le stockage (S3/MinIO)"
    )
    file_size = models.BigIntegerField(
        help_text="Taille du fichier en octets"
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True
    )
    
    # Métadonnées
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Gestion du cycle de vie
    expiration_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date d'expiration du document"
    )
    is_archived = models.BooleanField(
        default=False,
        help_text="Document archivé"
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Sécurité
    is_public = models.BooleanField(
        default=False,
        help_text="Accessible publiquement"
    )
    checksum = models.CharField(
        max_length=64,
        blank=True,
        help_text="Checksum MD5/SHA256 du fichier"
    )
    
    class Meta:
        app_label = 'core'
        db_table = 'common_document'
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['type_document']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['is_archived']),
        ]
    
    def __str__(self):
        return f"{self.nom} ({self.type_document})"
    
    def archive(self):
        """Archive le document."""
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save()


