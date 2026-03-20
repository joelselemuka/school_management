"""
Modèles pour la gestion des événements et actualités de l'école.
"""

from django.db import models
from django.conf import settings
from core.models import AnneeAcademique


class Event(models.Model):
    """
    Modèle pour les événements de l'école.
    
    Exemples: Journée portes ouvertes, Spectacle de fin d'année,
              Réunion parents-professeurs, Examens, Vacances, etc.
    """
    
    TYPE_CHOICES = [
        ('academique', 'Événement Académique'),
        ('sportif', 'Événement Sportif'),
        ('culturel', 'Événement Culturel'),
        ('administratif', 'Événement Administratif'),
        ('social', 'Événement Social'),
        ('autre', 'Autre'),
    ]
    
    STATUT_CHOICES = [
        ('planifie', 'Planifié'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('annule', 'Annulé'),
        ('reporte', 'Reporté'),
    ]
    
    titre = models.CharField(max_length=200, verbose_name="Titre de l'événement")
    description = models.TextField(verbose_name="Description")
    type_evenement = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='autre',
        verbose_name="Type d'événement"
    )
    
    date_debut = models.DateTimeField(verbose_name="Date et heure de début")
    date_fin = models.DateTimeField(
        verbose_name="Date et heure de fin",
        null=True,
        blank=True
    )
    
    lieu = models.CharField(
        max_length=200,
        verbose_name="Lieu",
        blank=True
    )
    
    organisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='evenements_organises',
        verbose_name="Organisateur"
    )
    
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='planifie',
        verbose_name="Statut"
    )
    
    annee_academique = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.CASCADE,
        related_name='evenements',
        verbose_name="Année académique"
    )
    
    participants_attendus = models.PositiveIntegerField(
        default=0,
        verbose_name="Nombre de participants attendus"
    )
    
    image = models.ImageField(
        upload_to='events/images/',
        null=True,
        blank=True,
        verbose_name="Image de l'événement"
    )
    
    est_public = models.BooleanField(
        default=True,
        verbose_name="Visible publiquement"
    )
    
    inscription_requise = models.BooleanField(
        default=False,
        verbose_name="Inscription requise"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ['-date_debut']
        indexes = [
            models.Index(fields=['date_debut']),
            models.Index(fields=['type_evenement']),
            models.Index(fields=['statut']),
        ]
    
    def __str__(self):
        return f"{self.titre} - {self.date_debut.strftime('%d/%m/%Y')}"
    
    @property
    def est_passe(self):
        """Vérifie si l'événement est passé."""
        from django.utils import timezone
        date_reference = self.date_fin if self.date_fin else self.date_debut
        return date_reference < timezone.now()
    
    @property
    def est_en_cours(self):
        """Vérifie si l'événement est en cours."""
        from django.utils import timezone
        now = timezone.now()
        if self.date_fin:
            return self.date_debut <= now <= self.date_fin
        return False


class Actualite(models.Model):
    """
    Modèle pour les actualités et nouvelles de l'école.
    
    Exemples: Annonces importantes, Succès d'élèves, Nouveautés,
              Informations générales, etc.
    """
    
    CATEGORIE_CHOICES = [
        ('annonce', 'Annonce'),
        ('succes', 'Succès'),
        ('info', 'Information'),
        ('alerte', 'Alerte'),
        ('nouveau', 'Nouveauté'),
        ('autre', 'Autre'),
    ]
    
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('publie', 'Publié'),
        ('archive', 'Archivé'),
    ]
    
    titre = models.CharField(max_length=250, verbose_name="Titre")
    sous_titre = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Sous-titre"
    )
    contenu = models.TextField(verbose_name="Contenu")
    
    categorie = models.CharField(
        max_length=20,
        choices=CATEGORIE_CHOICES,
        default='info',
        verbose_name="Catégorie"
    )
    
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='brouillon',
        verbose_name="Statut"
    )
    
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='actualites',
        verbose_name="Auteur"
    )
    
    annee_academique = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.CASCADE,
        related_name='actualites',
        verbose_name="Année académique"
    )
    
    image_principale = models.ImageField(
        upload_to='actualites/images/',
        null=True,
        blank=True,
        verbose_name="Image principale"
    )
    
    fichier_joint = models.FileField(
        upload_to='actualites/fichiers/',
        null=True,
        blank=True,
        verbose_name="Fichier joint"
    )
    
    est_une_alerte = models.BooleanField(
        default=False,
        verbose_name="Marquer comme alerte importante"
    )
    
    est_epingle = models.BooleanField(
        default=False,
        verbose_name="Épingler en haut"
    )
    
    date_publication = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de publication"
    )
    
    date_expiration = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'expiration"
    )
    
    vues = models.PositiveIntegerField(
        default=0,
        verbose_name="Nombre de vues"
    )
    
    tags = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Tags (séparés par des virgules)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Actualité"
        verbose_name_plural = "Actualités"
        ordering = ['-est_epingle', '-date_publication', '-created_at']
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['categorie']),
            models.Index(fields=['date_publication']),
            models.Index(fields=['-est_epingle', '-date_publication']),
        ]
    
    def __str__(self):
        return self.titre
    
    @property
    def est_active(self):
        """Vérifie si l'actualité est active (publiée et non expirée)."""
        from django.utils import timezone
        if self.statut != 'publie':
            return False
        if self.date_expiration and self.date_expiration < timezone.now():
            return False
        return True
    
    def incrementer_vues(self):
        """Incrémente le compteur de vues."""
        self.vues += 1
        self.save(update_fields=['vues'])
    
    def get_tags_list(self):
        """Retourne la liste des tags."""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []


class InscriptionEvenement(models.Model):
    """
    Modèle pour gérer les inscriptions aux événements.
    """
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('confirme', 'Confirmé'),
        ('annule', 'Annulé'),
    ]
    
    evenement = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='inscriptions',
        verbose_name="Événement"
    )
    
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inscriptions_evenements',
        verbose_name="Participant"
    )
    
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name="Statut"
    )
    
    nombre_accompagnants = models.PositiveIntegerField(
        default=0,
        verbose_name="Nombre d'accompagnants"
    )
    
    commentaire = models.TextField(
        blank=True,
        verbose_name="Commentaire"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Inscription à un événement"
        verbose_name_plural = "Inscriptions aux événements"
        unique_together = ['evenement', 'participant']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.participant} - {self.evenement.titre}"
