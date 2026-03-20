from django.db import models
from django.conf import settings

NOTIF_TYPE = [
    ("system", "Système"),
    ("info", "Information"),
    ("alerte", "Alerte"),
]

CANAL_CHOICES = [
    ("web", "Web"),
    ("email", "Email"),
    ("sms", "SMS"),
    ("push", "Push"),
]

STATUS_CHOICES = [
    ("queued", "En file"),
    ("sent", "Envoyée"),
    ("failed", "Échouée"),
]

class Notification(models.Model):
    titre = models.CharField(max_length=128)
    message = models.TextField()
    type = models.CharField(max_length=32, choices=NOTIF_TYPE, default="info")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class NotificationUser(models.Model):
    notification = models.ForeignKey(
        Notification,
        related_name="recipients",
        on_delete=models.CASCADE
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

  
    class Meta:
        unique_together = ("notification", "user")
        indexes = [
            models.Index(fields=["user", "is_read"]),
        ]


class NotificationDelivery(models.Model):
    notification_user = models.ForeignKey(
        NotificationUser,
        on_delete=models.CASCADE
    )

    canal = models.CharField(max_length=32, choices=CANAL_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)

    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["canal", "status"]),
        ]


class NotificationPreference(models.Model):
    """Préférences de notification d'un utilisateur."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Canaux activés
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    
    # Types de notifications
    notes_published = models.BooleanField(
        default=True,
        help_text="Notifications pour publication de notes"
    )
    absences = models.BooleanField(
        default=True,
        help_text="Notifications pour absences"
    )
    paiements = models.BooleanField(
        default=True,
        help_text="Notifications pour paiements"
    )
    annonces = models.BooleanField(
        default=True,
        help_text="Notifications pour annonces générales"
    )
    chat_messages = models.BooleanField(
        default=True,
        help_text="Notifications pour messages de chat"
    )
    
    # Fréquence
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immédiat'),
            ('daily', 'Quotidien'),
            ('weekly', 'Hebdomadaire'),
            ('disabled', 'Désactivé'),
        ],
        default='immediate'
    )
    
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Début des heures silencieuses"
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="Fin des heures silencieuses"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communication_notificationpreference'
        verbose_name = 'Préférence de Notification'
        verbose_name_plural = 'Préférences de Notifications'
    
    def __str__(self):
        return f"Préférences de {self.user.username}"


# ============================================================================
# CHAT INTER-SCOLAIRE
# ============================================================================

class ChatRoom(models.Model):
    """Salle de chat pour une classe ou un groupe."""
    
    nom = models.CharField(max_length=200)
    type_room = models.CharField(
        max_length=20,
        choices=[
            ('classe', 'Chat de Classe'),
            ('groupe', 'Groupe Privé'),
            ('general', 'Général'),
        ],
        default='classe'
    )
    classe = models.ForeignKey(
        'academics.Classe',
        on_delete=models.CASCADE,
        related_name='chat_rooms',
        null=True,
        blank=True,
        help_text="Classe associée (pour type=classe)"
    )
    description = models.TextField(blank=True, null=True)
    est_modere = models.BooleanField(
        default=True,
        help_text="Les messages nécessitent une modération"
    )
    membres = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ChatRoomMember',
        related_name='chat_rooms'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_chat_rooms'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'communication_chatroom'
        verbose_name = 'Salle de Chat'
        verbose_name_plural = 'Salles de Chat'
        indexes = [
            models.Index(fields=['type_room']),
            models.Index(fields=['classe']),
            models.Index(fields=['actif']),
        ]
    
    def __str__(self):
        return self.nom


class ChatRoomMember(models.Model):
    """Membre d'une salle de chat."""
    
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=[
            ('membre', 'Membre'),
            ('moderateur', 'Modérateur'),
            ('admin', 'Administrateur'),
        ],
        default='membre'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Dernière lecture des messages"
    )
    notifications_enabled = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'communication_chatroommember'
        verbose_name = 'Membre de Chat'
        verbose_name_plural = 'Membres de Chat'
        unique_together = ('room', 'user')
        indexes = [
            models.Index(fields=['room']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.username} dans {self.room.nom}"


class ChatMessage(models.Model):
    """Message dans une salle de chat."""
    
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    type_message = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Texte'),
            ('file', 'Fichier'),
            ('image', 'Image'),
            ('system', 'Message Système'),
        ],
        default='text'
    )
    file_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL du fichier attaché"
    )
    is_moderated = models.BooleanField(default=False)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_messages'
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communication_chatmessage'
        verbose_name = 'Message de Chat'
        verbose_name_plural = 'Messages de Chat'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['room']),
            models.Index(fields=['sender']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"






# ============================================================================
# WEBHOOKS (INTÉGRATIONS EXTERNES)
# ============================================================================

class WebhookEndpoint(models.Model):
    """Configuration Webhook pour l'intégration avec des services externes."""
    name = models.CharField(max_length=128)
    url = models.URLField(max_length=500)
    secret = models.CharField(max_length=128, blank=True, null=True, help_text="Clé secrète (optionnelle)")
    events = models.JSONField(default=list, help_text="Liste des événements (ex: ['paiement.created', 'eleve.created'])")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'communication_webhookendpoint'
        verbose_name = 'Endpoint Webhook'
        verbose_name_plural = 'Endpoints Webhooks'

    def __str__(self):
        return f"{self.name} ({self.url})"

class WebhookDelivery(models.Model):
    """Historique des envois webhook."""
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_name = models.CharField(max_length=100)
    payload = models.JSONField()
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, null=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'communication_webhookdelivery'
        ordering = ['-created_at']

